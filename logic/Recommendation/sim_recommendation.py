import numpy as np
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from sklearn.preprocessing import normalize
import os

# -----------------------------------
# 1. FAISS 인덱스 로드
# -----------------------------------
os.environ["OPENAI_API_KEY"] = ""

import numpy as np
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from sklearn.preprocessing import normalize

# -----------------------------------
# 1. FAISS 인덱스 로드 및 정합 맞추기
# -----------------------------------
embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
db = FAISS.load_local(
    "logic/results/faiss_index",
    embedding_model,
    allow_dangerous_deserialization=True,
)

all_docs = list(db.docstore._dict.values())
n_index = db.index.ntotal
embeddings = np.array(db.index.reconstruct_n(0, n_index)).astype("float32")

# ⚠️ 길이 보정 (안전하게 맞추기)
min_len = min(len(all_docs), n_index)
embeddings = embeddings[:min_len]
all_docs = all_docs[:min_len]

학수번호 = [d["metadata"]["학수번호"] for d in all_docs]
분반 = [d["metadata"]["분반"] for d in all_docs]

# -----------------------------------
# 2. 사용자 프로필 정의
# -----------------------------------
user_courses = [
    "ACE2901",
    "ACE2902",
    "CHM1923",
    "CHM1927",
    "EEC1100",
    "EEC1102",
    "EEC1104",
    "EEC2100",
    "EEC2101",
    "EEC2102",
    "EEC2104",
    "EEC2106",
    "EEC2108",
    "EEC2110",
    "EEC2200",
    "EEC2202",
    "EEC2204",
    "EEC2206",
    "EEC2208",
    "EEC4100",
]

mask = np.isin(학수번호, user_courses)
taken_idx = np.where(mask)[0]

user_emb = embeddings[taken_idx].mean(axis=0, keepdims=True)
user_norm = normalize(user_emb, axis=1)
emb_norm = normalize(embeddings, axis=1)

# -----------------------------------
# 3. 유사도 계산 및 Top-100 추출
# -----------------------------------
sims = emb_norm @ user_norm.T
sims = sims.flatten()

top_100_idx = np.argsort(-sims)[:100]

# ✅ 안전 필터링
filtered_idx = [
    i for i in top_100_idx if i < len(학수번호) and 학수번호[i] not in user_courses
]
top_10_idx = filtered_idx[:10]

# -----------------------------------
# 4. 교과목명 연동
# -----------------------------------
df = pd.read_csv("logic/results/bert_embeddings.csv")

print("===== 상위 10개 추천 과목 =====")
for i in top_10_idx:
    code = 학수번호[i]
    section = 분반[i]
    row = df[df["학수번호"] == code]
    if not row.empty:
        name = row.iloc[0]["교과목명"]
    else:
        name = "(교과목명 없음)"
    print(f"{code}-{section} | {name} | 유사도: {sims[i]:.4f}")
