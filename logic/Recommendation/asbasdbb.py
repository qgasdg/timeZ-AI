from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os

os.environ["OPENAI_API_KEY"] = "sk-proj-..."  # 네 키

embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
db = FAISS.load_local(
    "faiss_index", embedding_model, allow_dangerous_deserialization=True
)

# InMemoryDocstore 접근
if hasattr(db.docstore, "_dict"):
    docs = db.docstore._dict
else:
    docs = db.docstore

print("인덱스 벡터 수:", db.index.ntotal)
print("메타데이터 수:", len(docs))

missing = db.index.ntotal - len(docs)
if missing > 0:
    print(f"\n⚠️ {missing}개의 벡터가 메타데이터 없이 존재합니다.")
    print("예상 원인: 중복 저장 또는 누적 add() 수행")

# 샘플 확인
print("\n=== 메타데이터 샘플 3개 ===")
for i, doc in enumerate(docs.values()):
    print(doc["metadata"])
    if i == 2:
        break
