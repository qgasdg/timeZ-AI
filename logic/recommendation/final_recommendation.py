import numpy as np
from sklearn.cluster import KMeans
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from sklearn.preprocessing import normalize
import os
import pandas as pd
from time import time


def final_recommendation(user_courses):
    s = time()
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.load_local(
        "logic/results/faiss_index",
        embedding_model,
        allow_dangerous_deserialization=True,
    )
    t1 = time()
    print(f"✅ FAISS 인덱스 로드 완료: {t1 - s:.2f}초 소요")

    # -------------------------------
    # 1. 전체 문서 및 임베딩 불러오기
    # -------------------------------
    all_docs = list(db.docstore._dict.values())
    n_index = db.index.ntotal

    course_code = [d["metadata"]["학수번호"] for d in all_docs]
    embeddings = np.array(db.index.reconstruct_n(0, n_index)).astype("float32")
    t2 = time()
    print(f"✅ 전체 문서 및 임베딩 로드 완료: {t2 - t1:.2f}초 소요")
    # -------------------------------
    # 2. 사용자 프로필 벡터 계산
    # -------------------------------
    mask = np.isin(course_code, user_courses)
    taken_indices = np.where(mask)[0]

    if len(taken_indices) == 0:
        raise ValueError("수강 과목과 매칭되는 데이터가 없습니다.")

    user_embeds = embeddings[taken_indices]
    user_profile = user_embeds.mean(axis=0, keepdims=True).astype("float32")
    user_norm = normalize(user_profile, axis=1).astype("float32")
    t3 = time()
    print(f"✅ 사용자 프로필 벡터 계산 완료: {t3 - t2:.2f}초 소요")
    # -------------------------------
    # 3. FAISS에서 Top-k 검색
    # -------------------------------
    k_search = min(1000, n_index)
    sims, idx = db.index.search(user_norm, k_search)  # sims.shape = (1, k)

    sims = sims[0]
    idx = idx[0]
    emb_norm = normalize(embeddings, axis=1)
    t4 = time()
    print(f"✅ FAISS Top-{k_search} 검색 완료: {t4 - t3:.2f}초 소요")
    # -------------------------------
    # 4. 후보 200개 추출
    # -------------------------------
    top_n = 1000
    top_idx = idx[:top_n]
    cand_embs = emb_norm[top_idx]
    t5 = time()
    print(f"✅ 후보 {top_n}개 추출 완료: {t5 - t4:.2f}초 소요")
    # -------------------------------
    # 5. KMeans (xQuAD용 intent cluster)
    # -------------------------------
    n_clusters = 10
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
    labels = kmeans.fit_predict(cand_embs)
    cluster_coverage = np.zeros(n_clusters)
    t6 = time()
    print(f"✅ KMeans 클러스터링 완료: {t6 - t5:.2f}초 소요")
    # -------------------------------
    # 6. 리랭킹 (최적화된 Max-Sum + xQuAD)
    # -------------------------------
    k_final = 500  # 최종 추천 개수
    selected = []

    # (1) 후보 간 내적 행렬 미리 계산 (1000x1000)
    cand_sim_matrix = cand_embs @ cand_embs.T  # cosine similarity

    # (2) 빠른 조회용 매핑
    sim_dict = {g: sims[i] for i, g in enumerate(idx)}
    top_to_local = {g: i for i, g in enumerate(top_idx)}

    # (3) 리랭킹 루프
    for _ in range(k_final):
        best_idx, best_score = None, -1e9

        for local_i, global_i in enumerate(top_idx):
            if global_i in selected:
                continue

            if selected:
                selected_locals = [top_to_local[j] for j in selected]
                avg_sim = np.mean(cand_sim_matrix[local_i, selected_locals])
            else:
                avg_sim = 0

            coverage_gain = 1 - cluster_coverage[labels[local_i]]
            score = 0.6 * sim_dict[global_i] - 0.25 * avg_sim + 0.15 * coverage_gain

            if score > best_score:
                best_idx, best_score = global_i, score
                best_local_idx = local_i

        selected.append(best_idx)
        cluster_coverage[labels[best_local_idx]] += 1 / k_final

    t7 = time()
    print(f"✅ 리랭킹 완료: {t7 - t6:.2f}초 소요")

    # -------------------------------
    # 7. 결과 매핑
    # -------------------------------
    selected_haknums = []
    for faiss_idx in selected:
        if faiss_idx in db.index_to_docstore_id:
            doc_id = db.index_to_docstore_id[faiss_idx]
            metadata = db.docstore._dict[doc_id]["metadata"]
            selected_haknums.append([metadata["학수번호"], metadata["분반"]])
        else:
            print(f"⚠️ 인덱스 {faiss_idx}는 docstore 매핑에서 찾을 수 없습니다.")

    return selected_haknums


if __name__ == "__main__":
    os.environ["OPENAI_API_KEY"] = ""
    user_courses = [
        # 기존 교양 과목
        # 추가 전공 및 교양 과목
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
        "GEB1107",
    ]

    recommendations = final_recommendation(user_courses)
    print("최종 추천 과목 학수번호:", recommendations)

    df = pd.read_csv(
        "logic/results/bert_embeddings.csv", usecols=["교과목명", "학수번호", "분반"]
    )

    for i in recommendations:
        row = df[df["학수번호"] == i[0]]
        if not row.empty:
            print(row["교과목명"].values[0])
        else:
            print(f"{i} 과목 정보를 찾을 수 없습니다.")

    print("\n=== GE 과목 추천 결과 (상위 10개) ===")
    # GE로 시작하는 과목만 필터링
    ge_courses = list(
        {i[0]: i for i in recommendations if i[0].startswith("GE")}.values()
    )

    # 상위 10개만 출력
    for i in ge_courses[:20]:
        row = df[df["학수번호"] == i[0]]
        if not row.empty:
            print(
                f"{row["교과목명"].values[0]:<30}, {row["학수번호"].values[0]}, {row["분반"].values[0]}"
            )
        else:
            print(f"{i} 과목 정보를 찾을 수 없습니다.")
