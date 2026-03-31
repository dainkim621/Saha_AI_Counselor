from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

PERSIST_DIR = "data/vector/chroma_db"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def main():
    embedding = HuggingFaceEmbeddings(model_name=MODEL_NAME)

    vectordb = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embedding
    )

    while True:
        query = input("\n질문 입력 (종료: exit): ").strip()
        if query.lower() == "exit":
            break

        results = vectordb.similarity_search_with_score(query, k=5)

        print("\n검색 결과")
        print("=" * 100)
        print("질문:", query)

        for i, (doc, score) in enumerate(results, start=1):
            print("\n" + "-" * 100)
            print(f"[{i}] score={score:.4f}")
            print("제목:", doc.metadata.get("title"))
            print("URL:", doc.metadata.get("url"))
            print("chunk_id:", doc.metadata.get("chunk_id"))
            print("내용:", doc.page_content[:500])


if __name__ == "__main__":
    main()