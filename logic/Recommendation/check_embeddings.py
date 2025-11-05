import pandas as pd

df = pd.read_csv("embeddings.csv")

# 결측값(빈칸 or NaN) 있는 행 필터링
missing_rows = df[df[["학수번호", "분반", "text"]].isnull().any(axis=1)]

print(f"빈 값이 있는 행 개수: {len(missing_rows)}")

# 상위 5개만 미리보기
if not missing_rows.empty:
    print(missing_rows.head())
