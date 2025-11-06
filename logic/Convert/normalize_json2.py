import pandas as pd
import re

INPUT = "syllabus_merged.csv"
OUTPUT = "syllabus_final.csv"

# 1️⃣ CSV 불러오기
df = pd.read_csv(INPUT, dtype=str).fillna("")

# 2️⃣ 키 이름 정규화
rename_map = {}
for c in df.columns:
    new_c = re.sub(r"\s+", "", c)  # 공백, 개행 제거

    if "전공능력및핵심역량" in new_c or "전공능력및" in new_c:
        new_c = "전공능력및핵심역량"
    elif "OfficeHour(상담시간)" in new_c or "OfficeHour" in new_c:
        new_c = "OfficeHour(상담시간)"

    rename_map[c] = new_c

df = df.rename(columns=rename_map)

# 3️⃣ '주차별 강의진행계획서' (공백 포함) 열만 제거
cols_to_drop = [c for c in df.columns if "주차별 강의진행계획서" in c]  # 공백 포함
df = df.drop(columns=cols_to_drop, errors="ignore")

# 4️⃣ 열 순서 재정렬
core_cols = [
    "교과목명",
    "학수번호",
    "분반",
    "담당교수명",
    "학점",
    "교과목영문명",
    "강의시간표",
    "강좌평가방법",
    "강의목표",
    "강의목표.목표1",
    "강의목표.목표2",
    "강의목표.목표3",
    "강의개요",
    "교재",
    "부교재및참고도서",
    "강의진행방식",
    "수업방법",
    "수강시유의사항",
    "전공능력및핵심역량",
    "교수프로필(자세히보기)",
    "OfficeHour(상담시간)",
    "특별지원관련",
]

eval_cols = [c for c in df.columns if c.startswith("평가기준")]
extra_cols = [c for c in df.columns if c not in core_cols + eval_cols + ["__filename"]]

ordered_cols = core_cols + eval_cols + ["__filename"] + extra_cols
ordered_cols = [c for c in ordered_cols if c in df.columns]

df = df[ordered_cols]

# 5️⃣ 저장
df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
print(
    f"✅ '{OUTPUT}' 저장 완료 — {len(cols_to_drop)}개 '주차별 강의진행계획서' 열만 삭제됨"
)
