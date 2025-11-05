import numpy as np
import pandas as pd
import ast
import matplotlib.pyplot as plt
from sklearn.metrics.pairwise import cosine_similarity


def load_embeddings() -> np.ndarray:

    # CSV 불러오기
    file_path = "logic/embeddings.csv"
    df = pd.read_csv(file_path)

    # 문자열 형태의 벡터를 실제 리스트로 변환
    df["embedding"] = df["embedding"].apply(ast.literal_eval)

    # numpy array로 변환
    embeddings = np.vstack(df["embedding"].values)

    return embeddings


def histogram(embeddings: np.ndarray):
    # 코사인 유사도 계산
    sim = cosine_similarity(embeddings)

    # 히스토그램 시각화
    plt.figure(figsize=(6, 4))
    plt.hist(sim.flatten(), bins=50)
    plt.title("Cosine Similarity Distribution")
    plt.xlabel("Cosine similarity")
    plt.ylabel("Frequency")
    plt.show()


def t_SNE(embeddings: np.ndarray):
    from sklearn.manifold import TSNE

    X_embedded = TSNE(n_components=2, perplexity=30, random_state=42).fit_transform(
        embeddings
    )
    plt.scatter(X_embedded[:, 0], X_embedded[:, 1])
    plt.title("t-SNE Embedding Visualization")
    plt.show()


# embeddings = np.load("logic/embeddings.npy")
file_path = "embeddings.csv"
df = pd.read_csv(file_path)
print(type(df.iloc[0]["분반"]))
