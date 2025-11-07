import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans


def visualize_clusters_3d(embeddings, n_clusters=10, random_state=42):
    """
    KMeans로 클러스터링한 뒤 PCA로 3D 시각화
    Parameters
    ----------
    embeddings : np.ndarray, shape (N, D)
        정규화된 임베딩 벡터 (예: emb_norm)
    n_clusters : int
        KMeans 군집 개수
    """
    # 1. KMeans 클러스터링
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=random_state)
    labels = kmeans.fit_predict(embeddings)

    # 2. PCA 3차원 축소
    pca = PCA(n_components=3)
    reduced = pca.fit_transform(embeddings)

    # 3. 시각화
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")

    scatter = ax.scatter(
        reduced[:, 0],
        reduced[:, 1],
        reduced[:, 2],
        c=labels,
        cmap="tab10",
        s=30,
        alpha=0.8,
    )

    ax.set_xlabel("PCA 1")
    ax.set_ylabel("PCA 2")
    ax.set_zlabel("PCA 3")
    ax.set_title(f"KMeans Clusters (k={n_clusters}) in 3D PCA space")
    plt.legend(*scatter.legend_elements(), title="Cluster", bbox_to_anchor=(1.05, 1))
    plt.tight_layout()
    plt.show()

    return labels, reduced


if __name__ == "__main__":
    from langchain_community.vectorstores import FAISS
    from langchain_openai import OpenAIEmbeddings
    import numpy as np
    import os

    os.environ["OPENAI_API_KEY"] = ""

    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.load_local(
        "faiss_index", embedding_model, allow_dangerous_deserialization=True
    )

    n_index = db.index.ntotal
    embeddings = np.array(db.index.reconstruct_n(0, n_index)).astype("float32")

    visualize_clusters_3d(embeddings, n_clusters=10)
