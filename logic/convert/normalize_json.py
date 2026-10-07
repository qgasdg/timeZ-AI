from pathlib import Path
import json
import pandas as pd
import re

FOLDER = Path("logic/syllabus/json")
OUTPUT = Path("syllabus_merged.csv")

# 1️⃣ 키 이름 통일 매핑
KEY_MAP = {
    # 공백/개행/따옴표 차이 보정
    "전공능력 및\n핵심역량": "전공능력 및 핵심역량",
    "전공능력 및\n 핵심역량": "전공능력 및 핵심역량",
    "Office Hour\n(상담시간)": "Office Hour(상담시간)",
    '강좌평가방법"': "강좌평가방법",
    "수업 방법": "수업방법",
    "평가기준\n세부내역": "평가기준 세부내역",
}

# 2️⃣ 필수 키 (없으면 결측치로 추가)
REQUIRED_KEYS = [
    "교과목명",
    "담당교수명",
    "학수번호",
    "분반",
    "학점",
    "교과목영문명",
    "강의시간표",
    "강좌평가방법",
    "전공능력 및 핵심역량",
    "교수프로필(자세히보기)",
    "강의목표",
    "강의개요",
    "강의진행방식",
    "수업방법",
    "특별지원관련",
    "평가기준",
    "주차별 강의진행계획서",
]


# 3️⃣ 키 정규화 함수
def normalize_key(k: str) -> str:
    k = k.strip()
    k = k.replace("\n", "").replace(" ", "")
    return KEY_MAP.get(k, k)


# 4️⃣ JSON flatten 함수
def flatten_json(data: dict, parent_key=""):
    items = {}
    for k, v in data.items():
        new_key = f"{parent_key}.{normalize_key(k)}" if parent_key else normalize_key(k)
        if isinstance(v, dict):
            items.update(flatten_json(v, new_key))
        else:
            items[new_key] = v
    return items


# 5️⃣ 전체 파일 로드 및 병합
records = []
for p in sorted(FOLDER.glob("*.json")):
    try:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ {p.name} 로드 실패: {e}")
        continue

    flat = flatten_json(data)
    flat["__filename"] = p.name  # 원본 파일명 추적
    records.append(flat)

df = pd.DataFrame(records)

# 6️⃣ 결측 필드 보정
for key in REQUIRED_KEYS:
    cols = [c for c in df.columns if c.endswith(key)]
    if not cols:
        df[key] = None  # 완전 누락 시 새로 추가

# 7️⃣ CSV 저장
df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
print(f"✅ 병합 완료: {len(df)}개 파일 → {OUTPUT.name}")
