from Fix_xlsx import fix_applynumberform_in_xlsx

from openpyxl import load_workbook
import pandas as pd
import json
import os
import re

from pprint import pprint


def extract_table_between(records: list[dict], start_idx: int, end_idx: int) -> dict:
    """
    여러 줄로 구성된 표를 key-value 구조로 병합 (ex: 평가 항목표)

    Parameters
    ----------
    records : list[dict]
        각 행이 딕셔너리로 구성된 리스트 (ex: [{'col0': '중간고사', 'col1': '기말고사', ...}, {...}])
    start_idx : int
        키가 들어있는 행의 인덱스
    end_idx : int
        값이 들어있는 행의 인덱스

    Returns
    -------
    dict
        key_row와 val_row를 매핑한 딕셔너리
    """
    if start_idx >= len(records) or end_idx >= len(records):
        raise IndexError("❌ 지정된 인덱스가 records 범위를 벗어났습니다.")

    key_row = records[start_idx]
    val_row = records[end_idx]

    # 키와 값의 교집합을 기준으로 병합
    keys = [v for v in key_row.values() if v]
    vals = [v for v in val_row.values() if v]

    # zip은 길이가 다르면 짧은 쪽 기준으로 매핑됨
    return dict(zip(keys, vals))


def extract_weekly_plan(df: pd.DataFrame) -> dict:
    weekly_data = {}
    current_week = None

    for _, row in df.iterrows():
        week = str(row[0]).strip() if pd.notna(row[0]) else None
        key = str(row[1]).strip() if pd.notna(row[1]) else None
        value = str(row[4]).strip() if pd.notna(row[4]) else None
        mode = str(row[14]).strip() if pd.notna(row[14]) else None

        if week and week.isdigit():
            current_week = f"{int(week)}주차"
            weekly_data[current_week] = {}

        if current_week and key and value:
            weekly_data[current_week][key] = value
        if current_week and mode:
            weekly_data[current_week]["강의방식"] = mode

    return weekly_data


def xlsx_to_json(fixed_path) -> dict:
    """
    📘 XLSX 파일을 표준 엑셀로 재저장 후 JSON(dict) 형태로 변환

    Parameters
    ----------
    file_path : str
        원본 XLSX 파일 경로

    Returns
    -------
    dict
        시트별 데이터가 담긴 딕셔너리 (Key: 시트명, Value: 내용)
    """

    # 2️⃣ 표준화된 XLSX 파일 읽기 (data_only=True)
    wb = load_workbook(fixed_path, data_only=True)
    ws = wb["1"]  # 1 * 16 * 87 -> 16 * 87 (reshape)

    rows = [[cell.value for cell in row] for row in ws.iter_rows()]  # XLSX -> 2D 리스트
    df = pd.DataFrame(rows)  # 2D 리스트 -> DataFrame

    # 문자열 포함 셀만 key-value로 정리
    # key: "col0", "col1", ... / value: 셀 값
    records = []
    for _, row in df.iterrows():
        row_dict = {}
        for idx, val in enumerate(row):
            if isinstance(val, str) and val.strip():
                row_dict[f"col{idx}"] = val.strip()
        if row_dict:
            records.append(row_dict)

    structured_data = {}

    # 3️⃣ 기본 Key-Value 매핑 (일반 텍스트 행들)
    for i, record in enumerate(records):
        vals = list(record.values())
        if vals and vals[0] == "학수번호":
            code_text = vals[1]  # "BNF2201-001 학점:3.0"

            # 정규식으로 학수번호, 분반, 학점 분리
            match = re.match(r"([A-Za-z]+\d+)-(\d+)\s*학점[:：]?([\d.]+)", code_text)
            if match:
                subject_code, division, credit = match.groups()
                structured_data["학수번호"] = subject_code
                structured_data["분반"] = division
                structured_data["학점"] = float(credit)
            else:
                # 정규식이 안 맞는 경우 원문 그대로 저장
                structured_data["학수번호_원본"] = code_text

            # 교과목영문명 처리
            if len(vals) >= 4:
                structured_data["교과목영문명"] = vals[3]
            continue
        if vals and vals[0] == "평 가 기 준":
            temp = i  # 평가 기준 행 인덱스 저장
            break  # 평가 기준 이후는 별도 처리
        if len(vals) >= 2:
            for j in range(0, len(vals) - 1, 2):
                key = vals[j]
                value = vals[j + 1]
                structured_data[key] = value

    # 4️⃣ 평가 기준 테이블 병합 추가 (temp, temp + 1 행)
    try:
        grading_info = extract_table_between(
            records, temp + 1, temp + 2
        )  # 평가 기준 표 추출
        if grading_info:
            structured_data["평가기준"] = grading_info
    except Exception as e:
        print(f"⚠️ 평가 테이블 추출 실패 (sheet '1'): {e}")

    # 평가 기준 세부 내역 처리 temp + 3 행
    vals = list(records[temp + 3].values())
    if vals and len(vals) >= 2:
        for j in range(0, len(vals) - 1, 2):
            key = vals[j]
            value = vals[j + 1]
            structured_data[key] = value

    # 5️⃣ 주차별 강의진행계획서 추출 및 추가 (temp + 4 행 이후)
    try:
        weekly_plan_df = df.iloc[temp + 4 :, :]  # ✅ 주차별 강의계획 영역
        weekly_plan = extract_weekly_plan(weekly_plan_df)
        if weekly_plan:
            structured_data["주차별 강의진행계획서"] = weekly_plan
    except Exception as e:
        print(f"⚠️ 주차별 강의계획 추출 실패 (sheet '1'): {e}")

    return structured_data


def save_json(data: dict, file_path: str) -> str:
    """
    📦 변환된 JSON 데이터를 파일로 저장하는 함수

    Parameters
    ----------
    data : dict
        저장할 데이터 (xlsx_to_json 함수의 반환값)
    file_path : str
        원본 XLSX 파일 경로 (이름 기준으로 json 파일 생성)

    Returns
    -------
    str : 저장된 json 파일 경로
    """
    base, _ = os.path.splitext(file_path)
    output_path = f"{base}.json"

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 파일 저장 완료: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ JSON 저장 실패: {e}")
        return ""


def group_weekly_lectures(course_json: dict) -> dict:
    """
    📘 '주 차': '구 분' 아래의 주차별 강의정보(1~15)를
        하나의 '주차별 강의' dict로 묶는 함수

    Parameters
    ----------
    course_json : dict
        강의계획서 JSON (예: {"1": {...}} 형태)

    Returns
    -------
    dict
        기존 정보 유지 + '주차별 강의' key 추가
    """
    result = {}

    for outer_key, info in course_json.items():
        info_copy = dict(info)  # 원본 복사
        weekly = {}
        keys = list(info.keys())

        for i in range(1, 17):
            str_i = str(i)
            if str_i in info_copy:
                idx = keys.index(str_i)
                next_key = keys[idx + 1] if idx + 1 < len(keys) else None

                if next_key and not next_key.isdigit():
                    topic = next_key
                    lecture_type = info_copy.get(next_key, "")
                    weekly[f"{i}주차"] = {"주제": topic, "형태": lecture_type}

                    # flat 데이터 제거 대상
                    del info_copy[str_i]
                    if topic in info_copy:
                        del info_copy[topic]

        # 주차별 강의 추가
        info_copy["주차별 강의"] = weekly
        result[outer_key] = info_copy

    return result


if __name__ == "__main__":
    xlsx_path = "logic/syllabus/xlsx"  # 원본 XLSX 폴더
    fixed_path = "logic/syllabus/fixed"  # 변환된 XLSX 저장 폴더
    json_path = "logic/syllabus/json"  # JSON 저장 폴더

    # 폴더 생성
    os.makedirs(fixed_path, exist_ok=True)
    os.makedirs(json_path, exist_ok=True)

    for file in os.listdir(xlsx_path):
        if not file.endswith(".xlsx"):
            continue

        # 파일별 경로 정의
        src_xlsx = os.path.join(xlsx_path, file)
        fixed_xlsx = os.path.join(fixed_path, file)
        json_file = os.path.join(json_path, os.path.splitext(file)[0] + ".json")

        print(f"📗 처리 중: {src_xlsx}")

        # 1️⃣ 비표준 XLSX를 표준 엑셀로 자동 재저장
        fix_applynumberform_in_xlsx(src_xlsx, fixed_xlsx)

        # 2️⃣ JSON 변환
        data = xlsx_to_json(fixed_xlsx)
        print("✅ 변환 완료")

        # 3️⃣ JSON 파일 저장
        try:
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ JSON 파일 저장 완료: {json_file}")
        except Exception as e:
            print(f"❌ JSON 저장 실패: {e}")
