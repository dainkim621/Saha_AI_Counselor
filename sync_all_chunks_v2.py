"""Synchronize validated saha_clean_chunks.jsonl into Notice without dropping tables.

Run from project root:
    python sync_all_chunks.py --dry-run
    python sync_all_chunks.py --apply

Requires app.database, app.models, python-dotenv, openai, SQLAlchemy.
New embeddings are checkpointed in SQLite before any DB mutations.
Each document is replaced in its own DB transaction. Existing DB-only documents are retained.
"""
import argparse
import hashlib
import json
import os
import sqlite3
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import inspect
from app.database import SessionLocal
from app.models import Notice

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "data/processed/saha_clean_chunks.jsonl"
CACHE = ROOT / "data/processed/embedding_sync_cache.sqlite3"
MODEL = "text-embedding-3-small"
EXPECTED_DIM = 1536


def digest(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def read_chunks(path):
    groups = defaultdict(list)
    seen_ids = set()
    with path.open(encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if not line.strip():
                continue
            chunk = json.loads(line)
            cid, did = chunk.get("chunk_id"), chunk.get("doc_id")
            value = chunk.get("chunk_text")
            if not cid or not did or not isinstance(value, str) or not value.strip():
                raise ValueError(f"Invalid chunk (id/doc_id/text): line {line_number}")
            if cid in seen_ids:
                raise ValueError(f"Duplicate chunk_id: {cid}")
            seen_ids.add(cid)
            groups[did].append(chunk)
    for did, parts in groups.items():
        parts.sort(key=lambda x: x.get("chunk_index", -1))
        if [p["chunk_index"] for p in parts] != list(range(len(parts))):
            raise ValueError(f"Non-contiguous chunk_index: {did}")
    return groups


def vector_as_list(value):
    if value is None:
        return None
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, str):
        value = json.loads(value)
    arr = [float(x) for x in value]
    if len(arr) != EXPECTED_DIM:
        raise ValueError(f"Unexpected embedding dimension: {len(arr)}")
    return arr


def cache_open():
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(CACHE))
    db.execute("""CREATE TABLE IF NOT EXISTS embeddings (
        model TEXT NOT NULL,
        hash TEXT NOT NULL,
        source_text TEXT NOT NULL,
        vector_json TEXT NOT NULL,
        PRIMARY KEY (model, hash)
    )""")
    db.commit()
    return db


def cached_vector(cache, source_text):
    row = cache.execute("SELECT source_text, vector_json FROM embeddings WHERE model=? AND hash=?",
                        (MODEL, digest(source_text))).fetchone()
    if not row:
        return None
    if row[0] != source_text:
        raise ValueError("Embedding hash collision")
    return vector_as_list(json.loads(row[1]))


def store_vector(cache, source_text, vector):
    cache.execute("INSERT OR REPLACE INTO embeddings(model, hash, source_text, vector_json) VALUES (?, ?, ?, ?)",
                  (MODEL, digest(source_text), source_text, json.dumps(vector, separators=(",", ":"))))
    cache.commit()


def to_db_value(name, value, column):
    # Align optional values with the existing Notice storage conventions.
    if name == "views" and value is None:
        return 0
    if name == "published_at" and (value is None or str(value).strip() == ""):
        return None
    if name == "published_at" and value:
        # Date columns need a date instance; text columns can use the original string.
        from sqlalchemy import Date, DateTime
        if isinstance(column.type, DateTime):
            return datetime.fromisoformat(str(value))
        if isinstance(column.type, Date):
            return date.fromisoformat(str(value)[:10])
    return value


def build_notice(chunk, vector, columns):
    payload = dict(chunk)
    payload["embedding"] = vector
    payload["source"] = payload.get("source") or "saha.go.kr"
    # Ignore JSONL-only fields not represented by actual DB columns.
    kwargs = {}
    for name, column in columns.items():
        if name in payload and name != "id":
            kwargs[name] = to_db_value(name, payload[name], column)
    return Notice(**kwargs)


def canonical_metadata(chunk, columns):
    # Only compare fields that exist in input and table, exclude embedding.
    keys = [k for k in chunk if k in columns and k not in ("id", "embedding")]
    return keys


def main():
    ap = argparse.ArgumentParser()
    run_mode = ap.add_mutually_exclusive_group(required=True)
    run_mode.add_argument("--dry-run", action="store_true")
    run_mode.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not INPUT.exists():
        raise SystemExit(f"Missing validated input: {INPUT}")
    groups = read_chunks(INPUT)
    columns = {c.name: c for c in inspect(Notice).local_table.columns}
    required = {"doc_id", "chunk_id", "chunk_index", "chunk_text", "embedding"}
    if not required.issubset(columns):
        raise RuntimeError(f"Notice columns missing: {required - set(columns)}")

    db = SessionLocal()
    cache = cache_open()
    try:
        # Read DB state before writing. Reuse existing embeddings based on exact text.
        old_rows = db.query(Notice).all()
        old_by_doc = defaultdict(list)
        existing_vectors = {}
        for row in old_rows:
            old_by_doc[row.doc_id].append(row)
            if row.chunk_text and row.embedding is not None and row.chunk_text not in existing_vectors:
                existing_vectors[row.chunk_text] = vector_as_list(row.embedding)
        db.rollback()  # finish read transaction

        new_ids, old_ids = set(groups), set(old_by_doc)
        retained_only = old_ids - new_ids
        changed = []
        metadata_only = []
        unchanged = []
        for did, chunks in groups.items():
            prior = old_by_doc.get(did, [])
            old_by_cid = {r.chunk_id: r for r in prior}
            text_match = len(prior) == len(chunks)
            metadata_diff = False
            if text_match:
                for ch in chunks:
                    row = old_by_cid.get(ch["chunk_id"])
                    if row is None or row.chunk_text != ch["chunk_text"] or row.embedding is None:
                        text_match = False
                        break
                    for k in canonical_metadata(ch, columns):
                        old_value = getattr(row, k)
                        new_value = to_db_value(k, ch[k], columns[k])
                        if k == "menu_path":
                            old_value = list(old_value) if old_value is not None else None
                        if old_value != new_value:
                            metadata_diff = True
            if not text_match:
                changed.append(did)
            elif metadata_diff:
                metadata_only.append(did)
            else:
                unchanged.append(did)

        to_write = [ch for did in changed for ch in groups[did]]
        cache_hits = sum(cached_vector(cache, ch["chunk_text"]) is not None for ch in to_write)
        need_unique = {ch["chunk_text"] for ch in to_write
                       if ch["chunk_text"] not in existing_vectors and cached_vector(cache, ch["chunk_text"]) is None}
        print(f"Input: {len(groups)} documents, {sum(map(len, groups.values()))} chunks")
        print(f"DB-only documents retained: {len(retained_only)}")
        print(f"Unchanged documents: {len(unchanged)}")
        print(f"Metadata-only documents (no re-embedding): {len(metadata_only)}")
        print(f"Documents needing replacement: {len(changed)} ({len(to_write)} chunks)")
        print(f"Existing DB texts with embeddings: {len(existing_vectors)}")
        print(f"Checkpoint-cache chunk hits: {cache_hits}")
        print(f"New unique embeddings required (estimate): {len(need_unique)}")
        if args.dry_run:
            print("DRY RUN: database not modified; API not called.")
            return

        load_dotenv(ROOT / ".env")
        if need_unique and not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY missing for new embeddings")
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"]) if need_unique else None

        # Apply metadata changes in place; preserve Notice IDs and embeddings.
        for i, did in enumerate(metadata_only, 1):
            try:
                rows = {row.chunk_id: row for row in db.query(Notice).filter(Notice.doc_id == did).all()}
                for chunk in groups[did]:
                    row = rows[chunk["chunk_id"]]
                    for name in canonical_metadata(chunk, columns):
                        new_value = to_db_value(name, chunk[name], columns[name])
                        if getattr(row, name) != new_value:
                            setattr(row, name, new_value)
                db.commit()
            except Exception:
                db.rollback()
                raise
            if i % 100 == 0 or i == len(metadata_only):
                print(f"Metadata updated: {i}/{len(metadata_only)} documents", flush=True)

        completed = 0
        for did in changed:
            new_chunks = groups[did]
            payloads = []
            # Ensure every embedding for this document is ready before deleting DB rows.
            for chunk in new_chunks:
                content = chunk["chunk_text"]
                v = existing_vectors.get(content)
                if v is None:
                    v = cached_vector(cache, content)
                if v is None:
                    if client is None:
                        raise RuntimeError("Embedding unexpectedly missing and OpenAI client unavailable")
                    response = client.embeddings.create(model=MODEL, input=content)
                    v = vector_as_list(response.data[0].embedding)
                    store_vector(cache, content, v)  # durable before DB change
                existing_vectors[content] = v
                payloads.append(build_notice(chunk, v, columns))

            try:
                db.query(Notice).filter(Notice.doc_id == did).delete(synchronize_session=False)
                db.add_all(payloads)
                db.commit()  # one document: atomic replace
                completed += 1
            except Exception:
                db.rollback()
                raise
            if completed % 25 == 0 or completed == len(changed):
                print(f"Committed: {completed}/{len(changed)} documents", flush=True)

        print("DONE. DB-only documents were not deleted.")
    finally:
        cache.close()
        db.close()


if __name__ == "__main__":
    main()
