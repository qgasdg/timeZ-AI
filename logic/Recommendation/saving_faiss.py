import pandas as pd
import numpy as np
import ast
from langchain_community.vectorstores import FAISS
from langchain_community.docstore import InMemoryDocstore
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores.faiss import dependable_faiss_import
import os

os.environ["OPENAI_API_KEY"] = (
    "REDACTED_OPENAI_KEY"  # 네 API 키 입력
)

# 1️⃣ CSV 불러오기 및 정제
df = pd.read_csv("embeddings.csv")
df["embedding"] = df["embedding"].apply(ast.literal_eval)

# 결측값 제거
df = df[df["학수번호"].notna()].reset_index(drop=True)

# 2️⃣ 분반 문자열 변환
df["분반"] = df["분반"].apply(lambda x: "" if pd.isna(x) else str(int(x)).zfill(3))

# 3️⃣ 메타데이터 구성 (교과목명 제외)
metadatas = [
    {"학수번호": row["학수번호"], "분반": row["분반"]} for _, row in df.iterrows()
]

# 4️⃣ 임베딩 및 ID 준비
embeddings = np.vstack(df["embedding"].values).astype("float32")
ids = df["학수번호"].tolist()

# 5️⃣ FAISS 인덱스 생성
faiss = dependable_faiss_import()
index = faiss.IndexFlatIP(embeddings.shape[1])
index.add(embeddings)

# 6️⃣ LangChain FAISS wrapping
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
db = FAISS(
    embedding_function=embedding_model,
    index=index,
    docstore=InMemoryDocstore(
        {ids[i]: {"page_content": "", "metadata": metadatas[i]} for i in range(len(df))}
    ),
    index_to_docstore_id={i: ids[i] for i in range(len(df))},
)

# 7️⃣ 저장
db.save_local("faiss_index")
print(f"✅ 새 FAISS 인덱스 저장 완료 (총 {len(df)}개, 교과목명 제외)")
