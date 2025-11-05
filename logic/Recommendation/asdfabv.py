import json
import os
from Utils import load_json_files  # 네 기존 유틸 사용

# 1. JSON 파일들 로드
json_files = load_json_files("logic/syllabus/json")

# 2. 교과목명 필터링
target = "프로네시스 세미나"
matches = [j for j in json_files if j.get("교과목명") == target]

# 3. 결과 출력
print(f"총 {len(matches)}개 파일이 '{target}' 과목명과 일치합니다.")
for i, m in enumerate(matches, 1):
    print(f"\n[{i}] 파일명: {m.get('파일명', '(이름 정보 없음)')}")
    for k, v in m.items():
        if k not in ["embedding"]:  # 임베딩 제외
            print(f"{k}: {v}")
