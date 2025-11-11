from sklearn.feature_extraction.text import TfidfVectorizer
import os
import json
from pprint import pprint
import re
from sklearn.metrics.pairwise import cosine_similarity

folder_path = "logic/syllabus/"
all_data = []

# JSON 파일들 불러오기
for file in os.listdir(folder_path):
    if file.endswith(".json"):
        with open(os.path.join(folder_path, file), "r", encoding="utf-8") as f:
            data = json.load(f)
            all_data.append(data)


# 2️⃣ value 합치기 + 간단한 텍스트 정제
def clean_text(text):
    text = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", text)
    return text.strip()


# 텍스트 전처리
docs = []
for d in all_data:
    text = " ".join([clean_text(str(v)) for v in d.values()])
    docs.append(text)

pprint(docs[0])

vectorizer = TfidfVectorizer(max_features=2000)  # 단어 수 제한
tfidf = vectorizer.fit_transform(docs)

# 코사인 유사도 계산
f, s = 0, 1  # 비교할 문서 인덱스 설정
sim = cosine_similarity(tfidf[f], tfidf[s])  # type: ignore
pprint((all_data[f]["교과목명"], all_data[s]["교과목명"]))
"""
전체로 했을 때
금융&병렬 : 0.16
컴네&병렬 : 0.20
금융&컴네 : 0.25
"""

pprint(f"코사인 유사도: {sim[0][0]:.4f}")
