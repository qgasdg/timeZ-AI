from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import pandas as pd  # CSV 저장용

# load_dotenv()
# client = OpenAI()

prompt_template = """/
다음 JSON에 포함된 4개 필드를 활용해서, 해당 강의를 *수강 전 학생 입장*에서 말하듯 자연스럽게 요약해줘.

말투는 선배가 후배한테 알려주듯, 현실적인 조언 느낌으로 써줘. '~된대', '~되거든', '~익힐 수 있을 거야'처럼 부드럽고 설득력 있게

사용할 필드:
- "전공능력 및 핵심역량"
- "강의목표"
- "강의진행방식"
- "주차별 강의진행계획서"

요약 형식:
- 총 2문장
- 문장 구조는 다음처럼 구성:
    1. 어떤 개념과 기술을 배우게 되는지 (전문용어 중심으로, 예: CUDA, Amdahl’s Law 등)
    2. 어떤 흐름으로 배울지 (초중후반 흐름, 이론/실습 비중, 실습 주제 중심)
    3. 수업 방식이나 체감 난이도 (실습 위주인지, 프로젝트 방식인지 등)

조건:
- 전문용어는 그대로 활용하고, 문장은 자연스럽고 간결하게
- 수업을 처음 듣는 학생들에게 알려주는 느낌 

아래 JSON을 읽고 위 기준대로 요약해줘:
{json_data}
"""

file_list = os.listdir("logic/syllabus/normalized_json")

csv_path = "summaries.csv"

csv_exists = os.path.exists(csv_path)

for file_name in sorted(file_list)[:100]:
    # JSON 파일만 대상으로 하고 싶으면 아래 if 유지
    if not file_name.lower().endswith(".json"):
        continue

    file_path = os.path.join("logic/syllabus/normalized_json", file_name)

    # JSON 로드
    with open(file_path, "r", encoding="utf-8") as f:
        file_contents = json.load(f)
        print(file_contents.get("course_code", ""))
