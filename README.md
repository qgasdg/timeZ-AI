# timeZ-AI

인하대학교 강의계획서를 임베딩해서, 학생이 이미 들은 과목을 바탕으로 다음에 들을 과목을 추천합니다.

- 강의계획서 2,161개(2025-2학기)를 벡터로 바꿔 FAISS 인덱스에 저장합니다.
- 들은 과목들의 벡터 평균을 사용자 프로필로 씁니다.
- 비슷한 과목을 찾은 뒤, 추천이 한 분야에 몰리지 않도록 다시 정렬합니다.

## 추천 방식

`logic/recommendation/final_recommendation.py`

1. **사용자 프로필**: 들은 과목(학수번호)의 임베딩 평균을 정규화합니다.
2. **후보 검색**: FAISS 내적 검색으로 후보 1,000개를 뽑습니다.
3. **주제 군집**: 후보를 KMeans로 10개 군집으로 나눕니다.
4. **재정렬** (MaxSum<sup>4</sup> + xQuAD<sup>5</sup>): 아래 점수가 가장 높은 과목을 하나씩 골라 500개를 채웁니다.

   ```
   score = 0.6 × 사용자 유사도 − 0.25 × 이미 고른 과목과의 평균 유사도 + 0.15 × 군집 커버리지 이득
   ```

`logic/recommendation/algorithms.py`에서 top-k<sup>1</sup>, threshold<sup>2</sup>, MMR<sup>3</sup>, MaxSum<sup>4</sup>, xQuAD<sup>5</sup>를 서로 비교할 수 있습니다.

### 사용한 기법

1. **top-k**: 사용자 프로필과 코사인 유사도가 높은 순으로 k개를 고릅니다.
2. **threshold**: 유사도가 임계값 이하인 과목만 남깁니다. 이미 들은 과목과 거의 같은 과목을 빼는 용도입니다.
3. **MMR** (Maximal Marginal Relevance): 사용자 유사도는 높이고, 이미 고른 과목 중 *가장 비슷한 것*과의 유사도는 깎아서 하나씩 고릅니다.
4. **MaxSum**: MMR과 같지만, 이미 고른 과목들과의 *평균* 유사도를 깎습니다. 한 과목에 덜 민감합니다.
5. **xQuAD**: 후보를 KMeans로 주제 군집으로 나눈 뒤, 아직 덜 뽑힌 군집의 과목에 가산점을 줍니다. 추천이 한 분야에 몰리지 않게 합니다.

최종 점수식의 두 번째 항이 MaxSum<sup>4</sup>, 세 번째 항이 xQuAD<sup>5</sup>에서 왔습니다.

## 폴더 구조

```
timeZ-AI/
├─ logic/
│  ├─ convert/          강의계획서 수집 → JSON 변환 → 정규화
│  ├─ recommendation/   임베딩, FAISS 저장, 추천, 시각화
│  │  └─ test/          실험용 스크립트와 노트북
│  └─ results/          임베딩 결과, FAISS 인덱스, 수집 대상 목록
├─ faiss_index/          FAISS 인덱스 (logic/results/faiss_index와 같은 벡터)
├─ aditional_function/   xls → JSON 변환 도구
└─ tsne_kmeans_cluster_view.html   t-SNE 3D 군집 시각화 결과
```

## 파이프라인

1. **수집**: `results/filtered_*.csv`의 강의 목록 → 강의계획서 xlsx·html
   - `convert/download_xlsx.py`, `convert/download_html.py`
2. **변환**: xlsx·html → 강의별 JSON
   - `convert/xlsx_to_json.py`, `convert/html_to_json.py`
3. **정규화**: JSON → 키를 통일한 CSV
   - `convert/normalize_json.py` → `normalize_json2.py` → `normalize_json3.py` → `convert_keys_to_english.py`
4. **임베딩**: 과목명·강의목표·강의개요 → 벡터
   - `recommendation/embedding.py` (OpenAI `text-embedding-3-small`)
   - `recommendation/bert_embedding.py` (`paraphrase-multilingual-MiniLM-L12-v2`)
5. **인덱스**: 임베딩 → `faiss_index/`
   - `recommendation/saving_faiss.py`
6. **추천**: 들은 과목 목록 → 추천 학수번호·분반
   - `recommendation/final_recommendation.py`
7. **시각화**: 임베딩 → t-SNE 3D + KMeans 그래프
   - `recommendation/visualization.ipynb`

> 강의계획서 원문(xlsx·html·JSON·CSV)은 저작권과 교수 개인정보 때문에 레포에 넣지 않았습니다. 1~4단계를 다시 돌리려면 1단계부터 직접 수집해야 합니다.

## 시작하기

Python 3.12 이상이 필요합니다. 스크립트가 f-string 안에서 같은 따옴표를 씁니다.

```bash
pip install pandas numpy scikit-learn faiss-cpu langchain-community langchain-openai openai sentence-transformers matplotlib plotly
```

수집 단계(1~2)까지 돌리려면 아래 패키지도 설치하세요.

```bash
pip install selenium webdriver-manager beautifulsoup4 requests openpyxl
```

### 환경변수

`.env.example`을 참고해 값을 export하세요.

| 이름 | 쓰는 곳 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | 임베딩, 추천 | OpenAI API 키 |
| `INHA_SESSION_ID` | 수집 스크립트 | sugang.inha.ac.kr 로그인 후 `ASP.NET_SessionId` 쿠키 값 |
| `DOWNLOAD_DIR` | 수집 스크립트 | 내려받을 폴더 (기본값 `~/Downloads`) |
| `PROJECT_ROOT` | 노트북 | 레포 루트 경로 (기본값은 노트북 위치 기준 상대경로) |

### 추천 실행

레포 루트에서 실행하세요. 들은 과목은 파일 아래쪽 `user_courses` 목록에서 바꿉니다.

```bash
python logic/recommendation/final_recommendation.py
```

## 라이선스

[MIT](LICENSE)
