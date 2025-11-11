import pandas as pd, ast

df = pd.read_csv("embeddings.csv")
df["embedding"] = df["embedding"].apply(ast.literal_eval)

print("임베딩 길이:", len(df["embedding"][0]))
