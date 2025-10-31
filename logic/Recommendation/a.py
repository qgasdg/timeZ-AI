import os, json, re
from collections import defaultdict
from typing import List, Dict, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

############################################
# 1) 데이터 로드 & 필드 선택 & 평탄화
############################################

# 전공 구분에 유리한 필드만 사용 (필요시 수정)
ALLOW_KEYS = {
    "교과목명",
    "교과목영문명",
    "강의목표",
    "강의개요",
    "주차별 강의진행계획서",
}

# 전공 구분에 방해가 되는 필드는 제외 (평가/오피스아워/공지/형식 요소)
DENY_KEYS = {
    "평가기준",
    "평가기준\n세부내역",
    "강좌평가방법",
    "수업 방법",
    "강의진행방식",
    "수강시유의사항",
    "특별지원관련",
    "Office Hour\n(상담시간)",
    "강의시간표",
    "교수프로필(자세히보기)",
    "부교재및참고도서",
    "교재",
}


def flatten_week_plan(week_plan: Dict[str, Any]) -> str:
    # 주차별 강의진행계획서의 주제/내용/과제 등을 문장으로 합침
    lines = []
    for wk, item in week_plan.items():
        if isinstance(item, dict):
            for k, v in item.items():
                lines.append(str(v))
        else:
            lines.append(str(item))
    return " ".join(lines)


def select_fields(doc: Dict[str, Any]) -> Dict[str, str]:
    picked = {}
    for k, v in doc.items():
        if k in DENY_KEYS:
            continue
        if k in ALLOW_KEYS:
            if k == "주차별 강의진행계획서" and isinstance(v, dict):
                picked[k] = flatten_week_plan(v)
            else:
                picked[k] = str(v)
    # 보조: 핵심 필드가 하나도 없으면 value 전체라도 사용
    if not picked:
        picked = {k: str(v) for k, v in doc.items() if k not in DENY_KEYS}
    return picked


############################################
# 2) 텍스트 정제: 교육 불용어 제거 + 기호/숫자 정리
############################################

EDU_STOPWORDS = set(
    """
강의 수업 평가 과제 출석 시험 퀴즈 토론 프로젝트 보고서 학습 이해 목표 개요 참고 교재 부교재 오피스아워 공지
상대평가 절대평가 성적 점수 배점 기준 기타 계 변경될수 있음 안내 실습 진행 방식 자료 교수 담당 담당교원
""".split()
)


def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\uac00-\ud7a3a-z0-9\s]", " ", text)  # 한글/영문/숫자/공백만
    text = re.sub(r"\s+", " ", text).strip()
    # 불용어 제거(완전일치 기준)
    tokens = [t for t in text.split() if t not in EDU_STOPWORDS and len(t) > 1]
    return " ".join(tokens)


############################################
# 3) 문서 만들기: 필드 가중치 적용(선택)
############################################

FIELD_WEIGHTS = {
    "교과목명": 2.0,
    "교과목영문명": 1.5,
    "강의목표": 3.0,
    "강의개요": 3.0,
    "주차별 강의진행계획서": 2.0,
}


def build_weighted_text(picked_fields: Dict[str, str]) -> str:
    parts = []
    for k, v in picked_fields.items():
        w = FIELD_WEIGHTS.get(k, 1.0)
        cleaned = clean_text(v)
        if cleaned:
            # 간단 가중치: 텍스트를 w배 반복(대안: TF-IDF는 ngram/가중합으로 흡수하니 이 정도도 충분)
            parts.append((" " + cleaned) * int(round(w)))
    return " ".join(parts).strip()


############################################
# 4) TF-IDF 유사도
############################################


def tfidf_similarity(texts: List[str]) -> np.ndarray:
    # 튜닝 포인트: n-gram, df 필터, sublinear_tf
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,  # 너무 희귀한 단어 제외 (데이터 적으면 1로)
        max_df=0.85,  # 너무 흔한 단어 제외
        sublinear_tf=True,
        norm="l2",
    )
    X = vectorizer.fit_transform(texts)
    return cosine_similarity(X)


############################################
# 5) BERT 임베딩 유사도(의미 기반)
############################################


def bert_similarity(
    texts: List[str],
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
) -> np.ndarray:
    model = SentenceTransformer(model_name)
    emb = model.encode(texts, normalize_embeddings=True)  # 코사인용 정규화
    return cosine_similarity(emb)


############################################
# 6) 하이브리드 유사도
############################################


def hybrid_similarity(texts: List[str], alpha: float = 0.65) -> np.ndarray:
    # alpha: 의미 임베딩 가중치
    S_tfidf = tfidf_similarity(texts)
    S_bert = bert_similarity(texts)
    return alpha * S_bert + (1 - alpha) * S_tfidf


############################################
# 7) 예시 실행:
############################################

if __name__ == "__main__":
    docs = []
    titles = []
    folder_path = "logic/syllabus/"

    # JSON 파일들 불러오기
    for file in os.listdir(folder_path):
        if file.endswith(".json"):
            with open(os.path.join(folder_path, file), "r", encoding="utf-8") as f:
                data = json.load(f)
                titles.append(data.get("교과목명", file))
                data = select_fields(data)
                data = build_weighted_text(data)
                docs.append(data)

    # 1) TF-IDF
    S_tfidf = tfidf_similarity(docs)
    print("[TF-IDF] cosine similarity matrix:")
    print(np.round(S_tfidf, 3))
    print()

    # 2) BERT
    S_bert = bert_similarity(docs)
    print("[BERT] cosine similarity matrix:")
    print(np.round(S_bert, 3))
    print()

    # 3) Hybrid
    S_h = hybrid_similarity(docs, alpha=0.65)
    print("[Hybrid] cosine similarity matrix:")
    print(np.round(S_h, 3))
    print()

    # 4) 제목별로 보기 좋게 출력
    print("==== Similarity Summary by Course ====")
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            print(
                f"{titles[i]} ↔ {titles[j]}",
                f"| TF-IDF: {S_tfidf[i,j]:.3f}",
                f"| BERT: {S_bert[i,j]:.3f}",
                f"| Hybrid: {S_h[i,j]:.3f}",
            )
    print("======================================")
