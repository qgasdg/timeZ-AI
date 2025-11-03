import os, json, re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import time

############################################
# 1) 데이터 로드 & 필드 선택 & 평탄화
############################################

ALLOW_KEYS = {
    "교과목명",
    "교과목영문명",
    "강의목표",
    "강의개요",
    "주차별 강의진행계획서",
}

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


def flatten_week_plan(week_plan: dict) -> str:
    lines = []
    for wk, item in week_plan.items():
        if isinstance(item, dict):
            for k, v in item.items():
                lines.append(str(v))
        else:
            lines.append(str(item))
    return " ".join(lines)


def select_fields(doc: dict) -> dict:
    picked = {}
    for k, v in doc.items():
        if k in DENY_KEYS:
            continue
        if k in ALLOW_KEYS:
            if k == "주차별 강의진행계획서" and isinstance(v, dict):
                picked[k] = flatten_week_plan(v)
            else:
                picked[k] = str(v)
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
    text = re.sub(r"[^\uac00-\ud7a3a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = [t for t in text.split() if t not in EDU_STOPWORDS and len(t) > 1]
    return " ".join(tokens)


############################################
# 3) 문서 만들기: 필드 가중치 적용(선택)
############################################

FIELD_WEIGHTS = {
    "교과목명": 1.0,
    "교과목영문명": 1.0,
    "강의목표": 1.0,
    "강의개요": 1.0,
    "주차별 강의진행계획서": 1.0,
}


def build_weighted_text(picked_fields: dict) -> str:
    parts = []
    for k, v in picked_fields.items():
        w = FIELD_WEIGHTS.get(k, 1.0)
        cleaned = clean_text(v)
        if cleaned:
            parts.append((" " + cleaned) * int(round(w)))
    return " ".join(parts).strip()


############################################
# 4) TF-IDF 유사도
############################################


def tfidf_similarity(texts: np.ndarray) -> np.ndarray:
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.85,
        sublinear_tf=True,
        norm="l2",
    )
    X = vectorizer.fit_transform(texts)

    start = time.time()
    x = cosine_similarity(X)
    end = time.time()
    print(f"TF-IDF similarity computed in {end - start:.2f} seconds")
    return x


############################################
# 5) BERT 임베딩 유사도(의미 기반)
############################################


def bert_similarity(
    texts: np.ndarray,
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
) -> np.ndarray:
    model = SentenceTransformer(model_name)
    emb = model.encode(
        texts.tolist(), normalize_embeddings=True
    )  # np.ndarray → list 변환
    start = time.time()
    emb = cosine_similarity(emb)
    end = time.time()
    print(f"BERT similarity computed in {end - start:.2f} seconds")
    return emb


############################################
# 6) 하이브리드 유사도
############################################


def hybrid_similarity(texts: np.ndarray, alpha: float = 0.65) -> np.ndarray:
    S_tfidf = tfidf_similarity(texts)
    S_bert = bert_similarity(texts)
    return alpha * S_bert + (1 - alpha) * S_tfidf


############################################
# 7) JSON 파일 불러오기
############################################


def load_json_files(folder_path: str) -> np.ndarray:
    all_data = []
    for file in os.listdir(folder_path):
        if file.endswith(".json"):
            with open(os.path.join(folder_path, file), "r", encoding="utf-8") as f:
                data = json.load(f)
                all_data.append(data)
    return np.array(all_data)


# 전처리
def preprocess_json(json: np.ndarray) -> np.ndarray:
    texts = []
    for doc in json:
        selected = select_fields(doc)
        text = build_weighted_text(selected)
        texts.append(text)
    return np.array(texts)


############################################
# 8) 실행 예시
############################################

if __name__ == "__main__":
    folder_path = "logic/syllabus/"
    texts = load_json_files(folder_path)
    titles = np.array(
        [os.path.splitext(f)[0] for f in os.listdir(folder_path) if f.endswith(".json")]
    )

    # TF-IDF
    S_tfidf = tfidf_similarity(texts)
    print("[TF-IDF] cosine similarity matrix:")
    print(np.round(S_tfidf, 3))
    print()

    # BERT
    S_bert = bert_similarity(texts)
    print("[BERT] cosine similarity matrix:")
    print(np.round(S_bert, 3))
    print()

    # Hybrid
    alpha = 0.65
    S_h = alpha * S_bert + (1 - alpha) * S_tfidf
    print("[Hybrid] cosine similarity matrix:")
    print(np.round(S_h, 3))
    print()

    # Summary 출력
    print("==== Similarity Summary by Course ====")
    n = len(titles)
    for i in range(n):
        for j in range(i + 1, n):
            print(
                f"{titles[i]} ↔ {titles[j]}",
                f"| TF-IDF: {S_tfidf[i,j]:.3f}",
                f"| BERT: {S_bert[i,j]:.3f}",
                f"| Hybrid: {S_h[i,j]:.3f}",
            )
    print("======================================")
