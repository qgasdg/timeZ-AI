from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from sklearn.preprocessing import normalize
from sklearn.cluster import KMeans
import numpy as np
import os


os.environ["OPENAI_API_KEY"] = ""


# ---------------------------------------------------------
# 1. 인덱스 로드 + 임베딩/메타데이터 정합 맞추기
# ---------------------------------------------------------
def load_index():
    """FAISS 인덱스 + 메타데이터 + 임베딩 로드 (길이 맞춰서 반환)"""
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.load_local(
        "faiss_index",
        embedding_model,
        allow_dangerous_deserialization=True,
    )

    all_docs = list(db.docstore._dict.values())

    n_index = db.index.ntotal

    embeddings = np.array(db.index.reconstruct_n(0, n_index)).astype("float32")

    학수번호 = [d["metadata"]["학수번호"] for d in all_docs]
    분반 = [d["metadata"]["분반"] for d in all_docs]

    return all_docs, 학수번호, 분반, embeddings


# ---------------------------------------------------------
# 2. 사용자 프로필 구성 (수강 과목 평균 임베딩)
# ---------------------------------------------------------
def build_user_profile(user_courses, 학수번호, embeddings):
    """수강 과목 기반 user profile 임베딩 생성 + 정규화된 전체 임베딩 반환"""
    mask = np.isin(학수번호, user_courses)
    taken_indices = np.where(mask)[0]

    if len(taken_indices) == 0:
        print("⚠️ 수강 과목과 매칭되는 데이터가 없습니다.")
        return None, None, None

    user_embeds = embeddings[taken_indices]
    user_profile = user_embeds.mean(axis=0, keepdims=True).astype("float32")

    user_norm = normalize(user_profile, axis=1).astype("float32")  # (1, D)
    emb_norm = normalize(embeddings, axis=1).astype("float32")  # (N, D)

    return user_norm[0], emb_norm, taken_indices  # user_vec: (D,)


# ---------------------------------------------------------
# 3. 코사인 유사도 계산
# ---------------------------------------------------------
def compute_similarities(user_vec, emb_norm):
    """코사인 유사도 전체 계산"""
    sims = emb_norm @ user_vec  # (N,)
    return sims


# ---------------------------------------------------------
# 4-1. 기본 Top-K 추천
# ---------------------------------------------------------
def recommend_topk(sims, all_docs, 학수번호, user_courses, k=30):
    """기본 유사도 Top-K 추천"""
    sorted_idx = np.argsort(-sims)
    recs = []

    max_len = min(len(all_docs), len(학수번호), len(sims))

    for i in sorted_idx:
        if i >= max_len:
            continue
        if 학수번호[i] in user_courses:
            continue
        meta = all_docs[i]["metadata"]
        recs.append(
            {
                "학수번호": meta["학수번호"],
                "분반": meta["분반"],
                "유사도": float(sims[i]),
            }
        )
        if len(recs) >= k:
            break

    return recs


# ---------------------------------------------------------
# 4-2. 임계값 기반 추천
# ---------------------------------------------------------
def recommend_threshold(sims, all_docs, 학수번호, user_courses, threshold=0.8):
    """임계값 이하인 과목만 추천"""
    max_len = min(len(all_docs), len(학수번호), len(sims))
    idx = np.where(sims <= threshold)[0]
    idx = [i for i in idx if i < max_len]

    # 유사도 큰 순으로 정렬
    idx = sorted(idx, key=lambda i: sims[i], reverse=True)

    recs = []
    for i in idx:
        if 학수번호[i] in user_courses:
            continue
        meta = all_docs[i]["metadata"]
        recs.append(
            {
                "학수번호": meta["학수번호"],
                "분반": meta["분반"],
                "유사도": float(sims[i]),
            }
        )
    return recs


# ---------------------------------------------------------
# 4-3. MMR 기반 추천
# ---------------------------------------------------------
def mmr_selection(
    user_vec,
    emb_norm,
    sims,
    all_docs,  # all_docs를 인자로 받는다
    학수번호,
    user_courses,
    k=30,
    lambda_mult=0.5,
):
    """
    MMR:
    score(j) = λ * sim(query, j) - (1-λ) * max_{s∈S} sim(j, s)
    """
    N = emb_norm.shape[0]
    max_len = min(N, len(all_docs), len(학수번호), len(sims))

    # 이미 수강한 과목은 후보에서 제외
    taken_mask = np.isin(학수번호[:max_len], user_courses)
    candidate_indices = [i for i in range(max_len) if not taken_mask[i]]

    selected = []
    selected_set = set()

    if not candidate_indices:
        return []

    # 1번째: 쿼리와 가장 유사한 것
    first = max(candidate_indices, key=lambda i: sims[i])
    selected.append(first)
    selected_set.add(first)

    while len(selected) < k and len(selected_set) < len(candidate_indices):
        best_idx = None
        best_score = -1e9

        for j in candidate_indices:
            if j in selected_set:
                continue

            if selected:
                diversity = max(float(emb_norm[j] @ emb_norm[s]) for s in selected)
            else:
                diversity = 0.0

            mmr_score = lambda_mult * float(sims[j]) - (1 - lambda_mult) * diversity

            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = j

        if best_idx is None:
            break

        selected.append(best_idx)
        selected_set.add(best_idx)

    recs = []
    for i in selected:
        meta = all_docs[i]["metadata"]
        recs.append(
            {
                "학수번호": meta["학수번호"],
                "분반": meta["분반"],
                "유사도": float(sims[i]),
            }
        )
    return recs


# ---------------------------------------------------------
# 4-4. Max-Sum(평균 겹침 기반) Diversification
# ---------------------------------------------------------
def maxsum_selection(
    user_vec,
    emb_norm,
    sims,
    all_docs,
    학수번호,
    user_courses,
    k=30,
    lambda_mult=0.5,
):
    """
    Max-Sum(여기서는 평균 겹침 기반) Diversification:
    score(j) = λ * sim(query, j) - (1-λ) * avg_{s∈S} sim(j, s)

    - MMR: '최대(sim)' 하나만 보고 패널티
    - Max-Sum: '평균(sim)'으로 패널티 → 리스트 전체와의 겹침을 더 부드럽게 고려
    """
    N = emb_norm.shape[0]
    max_len = min(N, len(all_docs), len(학수번호), len(sims))

    # 이미 수강한 과목 제외
    taken_mask = np.isin(학수번호[:max_len], user_courses)
    candidate_indices = [i for i in range(max_len) if not taken_mask[i]]

    selected = []
    selected_set = set()

    if not candidate_indices:
        return []

    # 첫 번째: 쿼리와 가장 유사한 것
    first = max(candidate_indices, key=lambda i: sims[i])
    selected.append(first)
    selected_set.add(first)

    while len(selected) < k and len(selected_set) < len(candidate_indices):
        best_idx = None
        best_score = -1e9

        for j in candidate_indices:
            if j in selected_set:
                continue

            if selected:
                sim_list = [float(emb_norm[j] @ emb_norm[s]) for s in selected]
                avg_sim_to_selected = sum(sim_list) / len(sim_list)
            else:
                avg_sim_to_selected = 0.0

            score = (
                lambda_mult * float(sims[j]) - (1 - lambda_mult) * avg_sim_to_selected
            )

            if score > best_score:
                best_score = score
                best_idx = j

        if best_idx is None:
            break

        selected.append(best_idx)
        selected_set.add(best_idx)

    recs = []
    for i in selected:
        meta = all_docs[i]["metadata"]
        recs.append(
            {
                "학수번호": meta["학수번호"],
                "분반": meta["분반"],
                "유사도": float(sims[i]),
            }
        )
    return recs


# ---------------------------------------------------------
# 4-5. xQuAD 스타일 Diversification (클러스터 기반 coverage)
# ---------------------------------------------------------
def xquad_selection(
    user_vec,
    emb_norm,
    sims,
    all_docs,
    학수번호,
    user_courses,
    k=30,
    topn=300,
    n_clusters=10,
    lambda_rel=0.6,  # 관련성 비중
):
    """
    xQuAD 스타일 Diversification (의사 intent = 클러스터):

    1) 유사도 상위 topn 후보 선택
    2) 이 후보들을 KMeans로 n_clusters개로 나눔
    3) 각 클러스터를 '서로 다른 주제/영역(intent)'로 보고,
       score(j) = λ * sim(q, j) + (1-λ) * coverage_gain(j)
       로 greedy하게 re-ranking

    coverage_gain(j):
      - j가 속한 클러스터가 지금까지 얼마나 덜 선택되었는지에 따라 가중
    """
    N = emb_norm.shape[0]
    max_len = min(N, len(all_docs), len(학수번호), len(sims))

    # 1) 유사도 상위 topn 후보
    sorted_idx = np.argsort(-sims)[: min(topn, max_len)]

    # 이미 수강한 과목 제외
    taken_mask = np.isin(학수번호[:max_len], user_courses)
    candidate_indices = [i for i in sorted_idx if not taken_mask[i]]

    if not candidate_indices:
        return []

    # 2) 후보 임베딩으로 KMeans 클러스터링
    cand_embs = emb_norm[candidate_indices]
    n_clusters = min(n_clusters, len(candidate_indices))

    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = kmeans.fit_predict(cand_embs)

    # 각 global index → cluster id 매핑
    idx_to_cluster = {
        global_i: int(labels[local_i])
        for local_i, global_i in enumerate(candidate_indices)
    }

    # 클러스터별 coverage (0 ~ 1)
    cluster_coverage = np.zeros(n_clusters, dtype=float)

    selected = []
    selected_set = set()

    while len(selected) < k and len(selected_set) < len(candidate_indices):
        best_idx = None
        best_score = -1e18

        for j in candidate_indices:
            if j in selected_set:
                continue

            c = idx_to_cluster[j]

            # coverage_gain: '덜 뽑힌 클러스터'일수록 크게
            coverage_gain = 1.0 - cluster_coverage[c]

            score = lambda_rel * float(sims[j]) + (1 - lambda_rel) * coverage_gain

            if score > best_score:
                best_score = score
                best_idx = j

        if best_idx is None:
            break

        selected.append(best_idx)
        selected_set.add(best_idx)

        # 선택된 클러스터 coverage 업데이트
        c_sel = idx_to_cluster[best_idx]
        cluster_coverage[c_sel] = min(1.0, cluster_coverage[c_sel] + 1.0 / k)

    recs = []
    for i in selected:
        meta = all_docs[i]["metadata"]
        recs.append(
            {
                "학수번호": meta["학수번호"],
                "분반": meta["분반"],
                "유사도": float(sims[i]),
                "클러스터": idx_to_cluster[i],
            }
        )
    return recs


# ---------------------------------------------------------
# 5. 결과 집합 비교 (교집합/차집합)
# ---------------------------------------------------------
def compare_sets(results):
    def key(r):
        return f"{r['학수번호']}_{r['분반']}"

    topk_set = {key(r) for r in results["topk"]}
    thr_set = {key(r) for r in results["threshold"]}
    mmr_set = {key(r) for r in results["mmr"]}
    maxsum_set = {key(r) for r in results["maxsum"]}
    xquad_set = {key(r) for r in results["xquad"]}

    print("\n[집합 크기]")
    print("Top-K      :", len(topk_set))
    print("Threshold  :", len(thr_set))
    print("MMR        :", len(mmr_set))
    print("MaxSum     :", len(maxsum_set))
    print("xQuAD      :", len(xquad_set))

    print("\n[Top-K ∩ MMR ∩ MaxSum ∩ xQuAD 교집합 크기]")
    common = topk_set & mmr_set & maxsum_set & xquad_set
    print("공통 과목 수:", len(common))

    print("\n[Top-K에만 있는 과목 예시 5개]")
    for x in list(topk_set - (mmr_set | maxsum_set | xquad_set))[:5]:
        print("  ", x)

    print("\n[xQuAD에만 있는 과목 예시 5개]")
    for x in list(xquad_set - topk_set)[:5]:
        print("  ", x)


# ---------------------------------------------------------
# 6. 전체 실험 실행
# ---------------------------------------------------------
def run_experiment(user_courses, k=30, threshold=0.5, lambda_mult=0.5):
    # 1. 인덱스/메타/임베딩 로드
    all_docs, 학수번호, 분반, embeddings = load_index()

    # 2. user profile 만들기
    user_vec, emb_norm, taken_indices = build_user_profile(
        user_courses, 학수번호, embeddings
    )
    if user_vec is None:
        return None

    # 3. 전체 코사인 유사도
    sims = compute_similarities(user_vec, emb_norm)

    # 디버그용 상위 유사도 확인하고 싶으면 주석 해제
    # debug_idx = np.argsort(-sims)[:20]
    # print("\n[상위 20개 유사도]")
    # print([round(float(sims[i]), 4) for i in debug_idx])

    # 4-1. Top-K
    rec_topk = recommend_topk(sims, all_docs, 학수번호, user_courses, k=k)

    # 4-2. Threshold
    rec_threshold = recommend_threshold(
        sims, all_docs, 학수번호, user_courses, threshold=threshold
    )

    # 4-3. MMR
    rec_mmr = mmr_selection(
        user_vec,
        emb_norm,
        sims,
        all_docs,
        학수번호,
        user_courses,
        k=k,
        lambda_mult=lambda_mult,
    )

    # 4-4. Max-Sum
    rec_maxsum = maxsum_selection(
        user_vec,
        emb_norm,
        sims,
        all_docs,
        학수번호,
        user_courses,
        k=k,
        lambda_mult=lambda_mult,
    )

    # 4-5. xQuAD
    rec_xquad = xquad_selection(
        user_vec,
        emb_norm,
        sims,
        all_docs,
        학수번호,
        user_courses,
        k=k,
        topn=300,
        n_clusters=10,
        lambda_rel=0.6,
    )

    return {
        "topk": rec_topk,
        "threshold": rec_threshold,
        "mmr": rec_mmr,
        "maxsum": rec_maxsum,
        "xquad": rec_xquad,
    }


# ---------------------------------------------------------
# 7. 메인 실행
# ---------------------------------------------------------
if __name__ == "__main__":
    user_courses = [
        # 기존 교양 과목
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

    K = 30
    THRESHOLD = 0.5
    LAMBDA = 0.5

    results = run_experiment(
        user_courses,
        k=K,
        threshold=THRESHOLD,
        lambda_mult=LAMBDA,
    )

    print("\n[1. 기본 Top-K 유사도 추천]")
    print(len(results["topk"]), "개")
    for r in results["topk"][:10]:
        print(r)

    print(f"\n[2. 임계값 기반 추천 (Threshold > {THRESHOLD})]")
    print(len(results["threshold"]), "개")
    for r in results["threshold"][:10]:
        print(r)

    print(f"\n[3. MMR 기반 추천 (λ={LAMBDA})]")
    print(len(results["mmr"]), "개")
    for r in results["mmr"][:10]:
        print(r)

    print(f"\n[4. Max-Sum Diversification (λ={LAMBDA})]")
    print(len(results["maxsum"]), "개")
    for r in results["maxsum"][:10]:
        print(r)

    print("\n[5. xQuAD 스타일 Diversification]")
    print(len(results["xquad"]), "개")
    for r in results["xquad"][:10]:
        print(r)

    compare_sets(results)
