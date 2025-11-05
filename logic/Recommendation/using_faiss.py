import numpy as np
import pandas as pd
import ast
import faiss
from sklearn.preprocessing import normalize


def recommendation(user_courses):
    df["학수번호"] = df["학수번호"].astype(str).str.strip()

    # 3️⃣ 수강 과목 필터 + 중복 학수번호 제거
    mask = df["학수번호"].isin(user_courses)
    taken_df = df.loc[mask].drop_duplicates(subset="학수번호", keep="first")
    print(f"매칭된 과목 수 (중복 제거 후): {len(taken_df)}")

    # 4️⃣ 사용자 평균 임베딩 계산
    user_embeds = np.vstack(taken_df["embedding"].values)
    user_profile = user_embeds.mean(axis=0, keepdims=True).astype("float32")

    # 5️⃣ 임베딩 정규화 (코사인 유사도용)
    embeddings_norm = normalize(embeddings, axis=1).astype("float32")
    user_norm = normalize(user_profile, axis=1).astype("float32")

    # 6️⃣ FAISS Index 생성 (Inner Product → Cosine 유사도)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings_norm)

    # 7️⃣ 검색 (Top 200 정도 뽑고 그중 중복 제거)
    k = 200
    sims, idx = index.search(user_norm, k)

    # 8️⃣ 추천 결과 DataFrame 구성
    rec_df = df.iloc[idx[0]].copy()
    rec_df["similarity"] = sims[0]

    return rec_df["학수번호"]


if __name__ == "__main__":

    # 1️⃣ CSV 불러오기
    file_path = "embeddings.csv"
    df = pd.read_csv(file_path)
    df["embedding"] = df["embedding"].apply(ast.literal_eval)
    embeddings = np.vstack(df["embedding"].values).astype("float32")

    # 2️⃣ 사용자 수강 과목 (학수번호 기준)
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

    recommended_courses = recommendation(user_courses)
    print("추천 과목 학수번호:")
    print(recommended_courses.tolist())
