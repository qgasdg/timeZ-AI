from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os

os.environ["OPENAI_API_KEY"] = ""

embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
db = FAISS.load_local(
    "logic/results/faiss_index", embedding_model, allow_dangerous_deserialization=True
)

# InMemoryDocstore 접근
if hasattr(db.docstore, "_dict"):
    docs = db.docstore._dict
    print("InMemoryDocstore detected.")
else:
    docs = db.docstore
    print("Non-InMemoryDocstore detected.")

print(docs)
