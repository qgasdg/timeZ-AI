import pandas as pd
import json
import os

INPUT_CSV = "syllabus_english_keys.csv"
OUTPUT_FOLDER = "syllabus/normalized_json"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def clean_id(val):
    """학수번호나 분반이 1.0, 2.0 형태면 001, 002로 복원"""
    if pd.isna(val) or val == "":
        return ""
    s = str(val).strip()
    if s.replace(".", "", 1).isdigit():
        # 소수점 제거 후 정수로 변환
        num = int(float(s))
        # 학수번호는 보통 숫자만이면 3자리 zero-padding
        return f"{num:03d}" if len(s) <= 3 else str(num)
    return s


def unflatten_dict(flat_dict):
    """평탄화된 dict → 중첩 dict 복원"""
    result = {}
    for key, value in flat_dict.items():
        if pd.isna(value) or value == "":
            continue
        if key.startswith("__"):
            continue

        parts = str(key).split(".")
        d = result
        for p in parts[:-1]:
            if p not in d or isinstance(d[p], str):
                d[p] = {}
            d = d[p]
        d[parts[-1]] = value
    return result


# CSV 읽기 (전부 문자열로 강제)
df = pd.read_csv(INPUT_CSV, dtype=str).fillna("")

# 학수번호 / 분반 보정
df["course_code"] = df["course_code"].apply(clean_id)
df["class_number"] = df["class_number"].apply(clean_id)

print(f"📂 Loaded {len(df)} rows from {INPUT_CSV}")

for idx, row in df.iterrows():
    record = row.to_dict()
    nested = unflatten_dict(record)

    course_code = record.get("course_code", "unknown")
    class_number = record.get("class_number", "")

    filename = (
        f"{course_code}-{class_number}.json" if class_number else f"{course_code}.json"
    )
    filepath = os.path.join(OUTPUT_FOLDER, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(nested, f, ensure_ascii=False, indent=2)

print(f"✅ JSON 변환 완료 — {OUTPUT_FOLDER}/")
