import numpy as np
from sklearn.cluster import KMeans
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from sklearn.preprocessing import normalize
import os
import pandas as pd
from time import time
from pathlib import Path


def final_recommendation(user_courses):
    s = time()
    t1 = s

    # 0. 임베딩 모델 + FAISS 로드
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.load_local(
        str(FAISS_DIR),
        embedding_model,
        allow_dangerous_deserialization=True,
    )

    # -------------------------------
    # 1. 전체 문서 및 임베딩 불러오기
    #    👉 인덱스 순서에 맞게 메타데이터 정렬
    # -------------------------------
    n_index = db.index.ntotal
    print(f"총 인덱스 개수: {n_index}")

    """
    all_docs = list(db.docstore._dict.values())
    course_code = [d["metadata"]["학수번호"] for d in all_docs]
    """
    course_code = []
    for i in range(n_index):
        doc_id = db.index_to_docstore_id[i]  # 인덱스 → doc_id
        doc = db.docstore._dict[doc_id]  # doc_id → Document
        course_code.append(doc["metadata"]["학수번호"])

    embeddings = np.array(db.index.reconstruct_n(0, n_index)).astype("float32")
    t2 = time()
    print(f"✅ 전체 문서 및 임베딩 로드 완료: {t2 - t1:.2f}초 소요")

    # -------------------------------
    # 2. 사용자 프로필 벡터 계산
    # -------------------------------
    mask = np.isin(course_code, user_courses)
    taken_indices = np.where(mask)[0]

    print(f"매칭된 수강 과목 인덱스 수: {len(taken_indices)}")
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
    # 4. 후보 추출 + 수강 과목 제외
    # -------------------------------
    top_n = min(1000, len(idx))
    taken_set = set(taken_indices.tolist())

    # 검색 상위 결과 중에서 이미 수강한 과목은 제외
    top_idx = [g for g in idx[:top_n] if g not in taken_set]
    if not top_idx:
        raise ValueError("후보 과목(top_idx)이 비어 있습니다. 인덱스를 확인하세요.")

    cand_embs = emb_norm[top_idx]
    t5 = time()
    print(f"✅ 후보 {len(top_idx)}개 추출 완료 (수강 과목 제외): {t5 - t4:.2f}초 소요")

    # -------------------------------
    # 5. KMeans (xQuAD용 intent cluster)
    # -------------------------------
    n_clusters = min(10, len(top_idx))  # 후보보다 클 수 없게
    if n_clusters <= 1:
        print("⚠️ 클러스터 수가 1 이하라 KMeans를 생략합니다.")
        labels = np.zeros(len(top_idx), dtype=int)
    else:
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(cand_embs)
    cluster_coverage = np.zeros(n_clusters)
    t6 = time()
    print(f"✅ KMeans 클러스터링 완료: {t6 - t5:.2f}초 소요")

    # -------------------------------
    # 6. 리랭킹 (현재는 '유사도 점수만' 사용)
    # -------------------------------
    k_final = min(500, len(top_idx))  # 후보보다 많이 뽑지 않도록
    selected = []

    # (1) 후보 간 내적 행렬 (cosine similarity 근사)
    cand_sim_matrix = cand_embs @ cand_embs.T

    # (2) 빠른 조회용 매핑
    sim_dict = {g: sims[i] for i, g in enumerate(idx)}  # global index → sim score
    top_to_local = {g: i for i, g in enumerate(top_idx)}  # global → local idx

    for _ in range(k_final):
        best_idx, best_score = None, -1e9
        best_local_idx = None

        for local_i, global_i in enumerate(top_idx):
            if global_i in selected:
                continue

            # 1) 유저-후보 기본 유사도
            base_sim = sim_dict.get(global_i, -1e9)

            # 2) 이미 뽑힌 애들이랑 얼마나 겹치는지(다양도 penalty)
            if selected:
                selected_locals = [top_to_local[j] for j in selected]
                avg_sim = np.mean(cand_sim_matrix[local_i, selected_locals])
            else:
                avg_sim = 0.0

            # 3) 아직 덜 뽑힌 클러스터일수록 보너스
            coverage_gain = 1 - cluster_coverage[labels[local_i]]

            # 4) 최종 점수 (가중치는 네가 잡은 그대로 사용)
            score = 0.4 * base_sim - 0.25 * avg_sim + 0.15 * coverage_gain

            if score > best_score:
                best_idx, best_score = global_i, score
                best_local_idx = local_i

        if best_idx is None:
            break

        selected.append(best_idx)
        if n_clusters > 1:
            cluster_coverage[labels[best_local_idx]] += 1 / k_final
    t7 = time()
    print(f"✅ 리랭킹 완료: {t7 - t6:.2f}초 소요")

    # -------------------------------
    # 7. 결과 매핑 (학수번호, 분반)
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

    os.environ["OPENAI_API_KEY"] = ""  # 실제 키 설정 권장

    FAISS_DIR = Path("logic/results/faiss_index")

    print("🔎 FAISS_DIR:", FAISS_DIR)
    print("🔎 FAISS_DIR exists?:", FAISS_DIR.exists())
    print("🔎 index.faiss exists?:", (FAISS_DIR / "index.faiss").exists())
    user_courses = [
        # 기존 교양 과목 + 전공 과목들
        "GEB1112",
        "GEB1114",
        "GEB1116",
        "GEB1126",
        "GEB1143",
        "GEB1151",
        "GED4009-001",
        "GED2016-001",
        "GED5003-001",
        "GEE4007-001",
        "GEE4026-001",
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

    df = pd.read_csv("logic/results/syllabus_final.csv")

    print("\n=== 전체 추천 과목명 예시 (상위 20개) ===")
    for i in recommendations[:20]:
        row = df[df["학수번호"] == i[0]]
        if not row.empty:
            print(i[0], i[1], "-", row["교과목명"].values[0])
        else:
            print(f"{i} 과목 정보를 찾을 수 없습니다.")

    print("\n=== GE 과목 추천 결과 (상위 20개) ===")
    ge_courses = list(
        {i[0]: i for i in recommendations if i[0].startswith("GE")}.values()
    )

    for i in ge_courses[:20]:
        row = df[df["학수번호"] == i[0]]
        if not row.empty:
            print(i[0], i[1], "-", row["교과목명"].values[0])
        else:
            print(f"{i} 과목 정보를 찾을 수 없습니다.")
