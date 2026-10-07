import pandas as pd
import re

INPUT = "syllabus_final.csv"
OUTPUT = "syllabus_final_ordered.csv"

# 1️⃣ CSV 불러오기
df = pd.read_csv(INPUT, dtype=str).fillna("")

# 2️⃣ 키 이름 통일
rename_map = {}
for c in df.columns:
    new_c = re.sub(r"\s+", "", c)  # 공백 제거

    if "전공능력및핵심역량" in new_c or "전공능력및" in new_c:
        new_c = "전공능력및핵심역량"
    elif "OfficeHour" in new_c:
        new_c = "OfficeHour(상담시간)"
    rename_map[c] = new_c

df = df.rename(columns=rename_map)

# 3️⃣ 주차별 강의진행계획서 (공백 없는 것만 유지)
# 이미 주차별 강의진행계획서(공백 있는)는 제거된 상태로 가정
week_cols = [c for c in df.columns if "주차별강의진행계획서." in c]


# 주차번호, 하위항목 기준 정렬 (ex: 1주차.강의주제 → 1주차.강의내용 → 1주차.강의방식 → 1주차.시험및과제)
def sort_week_key(col):
    match = re.search(r"\.(\d{1,2})주차\.(.*)", col)
    if not match:
        return (99, col)
    week = int(match.group(1))
    field_order = ["강의주제", "강의내용", "강의방식", "시험및과제"]
    field = match.group(2)
    idx = field_order.index(field) if field in field_order else 99
    return (week, idx)


week_cols_sorted = sorted(week_cols, key=sort_week_key)

# 4️⃣ 주요 열 순서 정의
core_cols = [
    "교과목명",
    "학수번호",
    "학수번호_원본",
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

eval_cols = [
    "평가기준.중간고사",
    "평가기준.기말고사",
    "평가기준.출석",
    "평가기준.과제",
    "평가기준.퀴즈",
    "평가기준.토론",
    "평가기준.기타",
    "평가기준.계",
    "평가기준세부내역",
    "e-learning중간고사유형",
    "평가기준",
]

extra_cols = ["공학인증관련", "기타정보", "첨부파일", "__filename"]

# 5️⃣ 실제 순서 재조합
ordered_cols = (
    [c for c in core_cols if c in df.columns]
    + [c for c in eval_cols if c in df.columns]
    + week_cols_sorted
    + [c for c in extra_cols if c in df.columns]
)

# 남는 열(정의되지 않은)도 마지막에 추가
remaining = [c for c in df.columns if c not in ordered_cols]
ordered_cols += remaining

df = df[ordered_cols]

# 6️⃣ 저장
df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

print(f"✅ '{OUTPUT}' 저장 완료 — 총 {df.shape[1]}개 열, {df.shape[0]}개 행")
print(f"📚 주차별강의진행계획서 정렬된 열 수: {len(week_cols_sorted)}개")
