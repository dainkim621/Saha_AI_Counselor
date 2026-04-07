# Chroma 안에 들어있는 총 chunk 개수 출력, 벡터 DB에 몇 개 문서가 저장됐는지 확인
# collection count 수로 확인
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

embedding = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True}
)

vectordb = Chroma(
    persist_directory="data/vector/chroma_db",
    embedding_function=embedding
)

print("collection count =", vectordb._collection.count())