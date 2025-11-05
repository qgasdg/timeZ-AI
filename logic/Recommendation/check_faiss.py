from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os

os.environ["OPENAI_API_KEY"] = "sk-..."
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
db = FAISS.load_local(
    "faiss_index", embedding_model, allow_dangerous_deserialization=True
)

if hasattr(db.docstore, "_dict"):
    docs = db.docstore._dict
else:
    docs = db.docstore

print("인덱스 벡터 수:", db.index.ntotal)
print("메타데이터 수:", len(docs))

print("\n=== 메타데이터 샘플 ===")
for i, doc in enumerate(docs.values()):
    print(doc["metadata"])
    if i == 2:
        break
