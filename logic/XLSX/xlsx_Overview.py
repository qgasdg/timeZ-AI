import pandas as pd

# 전체 데이터프레임 읽기
file_path = "logic/syllabus/report.xlsx"
df = pd.read_excel(file_path, sheet_name="1")

# 데이터 요약: 상위 5행, 컬럼명, 데이터 타입, null 개수
data_overview = {
    "행 수": len(df),
    "열 수": len(df.columns),
    "열 이름": list(df.columns),
    "데이터 타입": df.dtypes.astype(str).to_dict(),
    "결측치 개수": df.isnull().sum().to_dict(),
    "상위 5행": df.head(5).to_dict(orient="records")
}

print(data_overview)