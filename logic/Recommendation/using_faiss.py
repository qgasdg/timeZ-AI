from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import numpy as np
from sklearn.preprocessing import normalize
import os

os.environ["OPENAI_API_KEY"] = (
    "REDACTED_OPENAI_KEY"
)


def recommendation(user_courses):
    # 1. FAISS 인덱스 로드
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.load_local(
        "faiss_index", embedding_model, allow_dangerous_deserialization=True
    )

    # 2. InMemoryDocstore 접근 (버전 호환)
    if hasattr(db.docstore, "_dict"):
        all_docs = list(db.docstore._dict.values())  # InMemoryDocstore 내부 dict
    else:
        all_docs = list(db.docstore.values())  # 이미 dict인 경우

    # 3. 인덱스
    n_index = db.index.ntotal

    # 4. 메타데이터 및 임베딩 추출
    학수번호 = [d["metadata"]["학수번호"] for d in all_docs]
    분반 = [d["metadata"]["분반"] for d in all_docs]
    embeddings = np.array(db.index.reconstruct_n(0, n_index)).astype("float32")

    # 5. 사용자 수강 과목 필터링
    mask = np.isin(학수번호, user_courses)
    taken_indices = np.where(mask)[0]

    if len(taken_indices) == 0:
        print("⚠️ 수강 과목과 매칭되는 데이터가 없습니다.")
        return []

    # 6. 사용자 평균 임베딩 계산
    user_embeds = embeddings[taken_indices]
    user_profile = user_embeds.mean(axis=0, keepdims=True).astype("float32")
    user_norm = normalize(user_profile, axis=1).astype("float32")

    # 7. 유사도 기반 검색 (Top 1000)
    k = min(1000, n_index)
    sims, idx = db.index.search(user_norm, k)

    # 8. 추천 결과 구성
    rec_indices = idx[0]
    recs = []
    for i in rec_indices:
        meta = all_docs[i]["metadata"]
        if meta["학수번호"] not in user_courses:
            recs.append([meta["학수번호"], meta["분반"]])

    return recs


if __name__ == "__main__":
    user_courses = [
        "GEB1112",
        "GEB1114",
        "GEB1116",
        "GEB1126",
        "GEB1143",
        "GEB1151",
        "GED4009",
        "GED2016",
        "GED5003",
        "GEE4007",
        "GEE4026",
    ]

    recs = recommendation(user_courses)
    print("\n추천 과목 (학수번호, 분반):")
    print(len(recs), "개")
    for r in recs[:10]:
        print(r)
