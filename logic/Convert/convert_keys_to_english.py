import pandas as pd
import re

INPUT = "syllabus_final_real.csv"
OUTPUT = "syllabus_english_keys.csv"

df = pd.read_csv(INPUT, dtype=str).fillna("")

# 기본 한글→영문 매핑
key_map = {
    "교과목명": "course_name",
    "담당교수명": "professor",
    "학수번호": "course_code",
    "분반": "class_number",
    "학점": "credit",
    "교과목영문명": "course_name_en",
    "강의시간표": "timetable",
    "강좌평가방법": "grading_method",
    "전공능력및핵심역량": "core_competency",
    "교수프로필(자세히보기)": "professor_profile",
    "강의목표": "objective",
    "강의목표.목표1": "objective.goal1",
    "강의목표.목표2": "objective.goal2",
    "강의목표.목표3": "objective.goal3",
    "강의개요": "overview",
    "교재": "textbook",
    "부교재및참고도서": "reference_book",
    "강의진행방식": "teaching_method",
    "수업방법": "class_method",
    "수강시유의사항": "precautions",
    "OfficeHour(상담시간)": "office_hour",
    "특별지원관련": "special_support",
    "평가기준.중간고사": "evaluation.midterm",
    "평가기준.기말고사": "evaluation.final",
    "평가기준.출석": "evaluation.attendance",
    "평가기준.과제": "evaluation.assignment",
    "평가기준.퀴즈": "evaluation.quiz",
    "평가기준.토론": "evaluation.discussion",
    "평가기준.기타": "evaluation.etc",
    "평가기준.계": "evaluation.total",
    "평가기준세부내역": "evaluation.detail",
    "평가기준": "evaluation",
    "e-learning중간고사유형": "elearning_exam_type",
    "공학인증관련": "engineering_certification",
    "기타정보": "etc_info",
    "첨부파일": "attachment",
    "__filename": "filename",
    "학수번호_원본": "original_course_code",
}


# 주차별 강의계획 키 패턴 매핑
def convert_weekly_plan(col):
    m = re.match(r"주차별강의진행계획서\.(\d{1,2})주차\.(.+)", col)
    if not m:
        return None
    week = int(m.group(1))
    subkey = m.group(2)
    sub_map = {
        "강의주제": "topic",
        "강의내용": "content",
        "강의방식": "method",
        "시험및과제": "exam_or_task",
    }
    eng_subkey = sub_map.get(subkey, subkey)
    return f"weekly_plan.week{week}.{eng_subkey}"


# 일반 키 변환 함수
def convert_key(col):
    # 1️⃣ 주차별 강의계획서 처리
    weekly = convert_weekly_plan(col)
    if weekly:
        return weekly
    # 2️⃣ 명시적 매핑
    if col in key_map:
        return key_map[col]
    # 3️⃣ 접두사 매칭 (예: 강의목표.목표1 → objective.goal1)
    for k, v in key_map.items():
        if col.startswith(k):
            return col.replace(k, v)
    # 4️⃣ fallback: 한글 제거
    return re.sub(r"[^A-Za-z0-9_.]", "_", col).lower().strip("_")


# 전체 컬럼 변환
df.columns = [convert_key(c) for c in df.columns]

# 저장
df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
print(f"✅ 모든 컬럼 영어로 변환 완료 — {OUTPUT}")
