
# row 문서 제목이 한쪽으로 쏠렸는지 보기
'''

import json
from collections import Counter

counter = Counter()
with open("data/raw/saha_docs.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        doc = json.loads(line)
        counter[doc.get("title","")] += 1

for title, cnt in counter.most_common(20):
    print(cnt, title)

'''



# URL이 한쪽으로 쏠렸는지 보기
'''
import json
from collections import Counter
from urllib.parse import urlparse

counter = Counter()
with open("data/raw/saha_docs.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        doc = json.loads(line)
        url = doc.get("url","")
        counter[url] += 1

for url, cnt in counter.most_common(20):
    print(cnt, url)
'''




# chunk가 같은 제목 중심으로 몰리는지 보기

'''
import json
from collections import Counter

counter = Counter()
with open("data/processed/saha_chunks.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        counter[item.get("title","")] += 1

for title, cnt in counter.most_common(30):
    print(cnt, title)
'''



# Chroma 안에 들어있는 총 chunk 개수 출력, 벡터 DB에 몇 개 문서가 저장됐는지 확인
'''
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
'''