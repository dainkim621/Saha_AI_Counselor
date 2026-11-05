import json
from collections import Counter, defaultdict
from pathlib import Path
from ai.rag.preprocessing.preprocess_exe import run_preprocessing_pipeline
from ai.rag.preprocessing.domains import process_general_docs

ROOT = Path('data')
CHUNK_FILE = ROOT / 'processed/saha_clean_chunks.jsonl'
SOURCES = {
    'general': ROOT / 'raw/saha_docs.jsonl',
    'civil': ROOT / 'raw/saha_civil_forms.jsonl',
    'bid': ROOT / 'raw/saha_bid_docs.jsonl',
    'waste': ROOT / 'raw/saha_waste_docs.jsonl',
    'passport': ROOT / 'raw/passport_forms.jsonl',
}

def load_jsonl(path):
    with open(path, encoding='utf-8') as stream:
        for row in stream:
            if row.strip():
                yield json.loads(row)

if not CHUNK_FILE.exists():
    raise SystemExit(f'파일 없음: {CHUNK_FILE}')

print('원본 -> 도메인 전처리 -> 청킹 재생성 결과와 저장 파일 비교 중...')
expected = run_preprocessing_pipeline({k: str(v) for k, v in SOURCES.items()})
actual = list(load_jsonl(CHUNK_FILE))

exp_map = {c['chunk_id']: c for c in expected}
act_map = {c['chunk_id']: c for c in actual}
exp_ids = Counter(c['chunk_id'] for c in expected)
act_ids = Counter(c['chunk_id'] for c in actual)
duplicate_ids = {k:v for k,v in act_ids.items() if v>1}
missing_ids = sorted(exp_map.keys() - act_map.keys())
extra_ids = sorted(act_map.keys() - exp_map.keys())
changed_ids = sorted(k for k in exp_map.keys() & act_map.keys() if exp_map[k]['chunk_text'] != act_map[k]['chunk_text'])

# 동일 doc_id 안에서 텍스트가 완전히 같은 청크를 검사한다.
text_counts_by_doc = defaultdict(Counter)
for chunk in actual:
    text_counts_by_doc[chunk['doc_id']][chunk['chunk_text']] += 1
exact_duplicate_rows = sum(n-1 for counts in text_counts_by_doc.values() for n in counts.values() if n > 1)
docs_with_exact_duplicates = sum(any(n>1 for n in counts.values()) for counts in text_counts_by_doc.values())

# 두 도메인에 동일 doc_id가 존재해도 각각 생성된 청크가 있는지 별도로 감사한다.
source_section_missing = []
for doc in load_jsonl(SOURCES['general']):
    refined = process_general_docs(doc)
    texts = [entry.get('text', '') for entry in (refined or [])]
    if doc.get('page_type') == 'staff':
        source_texts = [doc.get('text') or '']
    else:
        source_texts = [sec.get('text') or '' for sec in (doc.get('sections') or [])]
        if not source_texts:
            source_texts = [doc.get('text') or '']
    if any(s.strip() and not any(s in t for t in texts) for s in source_texts):
        source_section_missing.append({'doc_id': doc.get('doc_id'), 'title': doc.get('title')})

backup_sections = 0
backup_chars = 0
for doc in load_jsonl(SOURCES['general']):
    for sec in doc.get('sections') or []:
        if sec.get('block_type') == 'full_text_backup':
            backup_sections += 1
            backup_chars += len(sec.get('text') or '')

report = {
    'expected_chunk_count': len(expected),
    'actual_chunk_count': len(actual),
    'expected_duplicate_ids': sum(n-1 for n in exp_ids.values() if n>1),
    'actual_duplicate_ids': duplicate_ids,
    'missing_chunk_ids': missing_ids[:30],
    'missing_chunk_ids_count': len(missing_ids),
    'unexpected_chunk_ids': extra_ids[:30],
    'unexpected_chunk_ids_count': len(extra_ids),
    'different_chunk_text_ids': changed_ids[:30],
    'different_chunk_text_ids_count': len(changed_ids),
    'original_sections_not_found_in_refined': source_section_missing[:30],
    'original_sections_not_found_count': len(source_section_missing),
    'exact_duplicate_text_rows_within_document': exact_duplicate_rows,
    'documents_with_exact_duplicate_text': docs_with_exact_duplicates,
    'full_text_backup_section_count': backup_sections,
    'full_text_backup_characters': backup_chars,
}
path = ROOT / 'processed/saha_chunk_audit.json'
path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

for key in ['expected_chunk_count','actual_chunk_count','expected_duplicate_ids','missing_chunk_ids_count','unexpected_chunk_ids_count','different_chunk_text_ids_count','original_sections_not_found_count','exact_duplicate_text_rows_within_document','documents_with_exact_duplicate_text','full_text_backup_section_count']:
    print(f'{key}: {report[key]}')
print('상세 보고서:', path)

ok = (not duplicate_ids and report['expected_duplicate_ids'] == 0
      and len(expected) == len(actual)
      and not missing_ids and not extra_ids and not changed_ids
      and not source_section_missing)
print('최종 판정:', 'PASS (DB 반영 준비 가능)' if ok else 'FAIL (DB 반영 금지)')
if not ok:
    raise SystemExit(1)
