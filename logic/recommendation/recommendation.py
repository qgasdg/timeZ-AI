import numpy as np
import pandas as pd
import ast
from sklearn.metrics.pairwise import cosine_similarity

# 1. CSV 불러오기
file_path = "embeddings.csv"
df = pd.read_csv(file_path)
df["embedding"] = df["embedding"].apply(ast.literal_eval)
embeddings = np.vstack(df["embedding"].values)

# 2. 사용자 수강 과목 (학수번호만 사용)
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

# 문자열 정리
df["학수번호"] = df["학수번호"].astype(str).str.strip()

# 3. 수강 과목 필터 + 중복 학수번호 제거
mask = df["학수번호"].isin(user_courses)
taken_df = df.loc[mask].drop_duplicates(subset="학수번호", keep="first")
print(taken_df)

print(f"매칭된 과목 수 (중복 제거 후): {len(taken_df)}")

# 4. 평균 임베딩 계산
user_embeds = np.vstack(taken_df["embedding"].values)
user_profile = user_embeds.mean(axis=0).reshape(1, -1)

# 5. 전체 유사도 계산
sims = cosine_similarity(user_profile, embeddings).flatten()
df["similarity"] = sims

# 6. 수강 과목 제외 후 후보 생성
candidates = df.loc[~mask].sort_values("similarity", ascending=False)

# 7. 추천 목록 중복 제거 (교과목명 기준) 후 상위 10개 선택
recommendations = candidates.drop_duplicates(subset="text").head(10)

# 8. 결과 출력
print("=== 추천 강의 Top 10 (중복 제거) ===")
print(recommendations[["학수번호", "분반", "text", "similarity"]])
