import pandas as pd

df = pd.read_csv("syllabus_final_ordered.csv")

# '주차별강의진행계획서'가 포함된 모든 열 삭제
df = df.drop(
    columns=[c for c in df.columns if "주차별강의진행계획서" == c], errors="ignore"
)

# 결과 저장
df.to_csv("syllabus_final_no_weekplan.csv", index=False, encoding="utf-8-sig")

print("✅ '주차별강의진행계획서' 관련 모든 열 삭제 완료")
