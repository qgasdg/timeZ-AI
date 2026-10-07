from Utils import load_json_files

import numpy as np


ALLOW_KEYS = [
    "교과목명",
    "교과목영문명",
    "강의목표",
    "강의개요",
    "강의진행방식",
    "수업 방법",
    "강의시간표",
    "수강시유의사항",
    "부교재및참고도서",
    "전공능력 및\n핵심역량",
    "강좌평가방법",
    "주차별 강의진행계획서",
]


def flatten_week_plan(week_plan: dict) -> str:
    lines = []
    for _, item in week_plan.items():
        if isinstance(item, dict):
            for _, v in item.items():
                lines.append(str(v))
        else:
            lines.append(str(item))
    return " ".join(lines)


def select_fields(doc: dict) -> dict:
    picked = {}
    for k, v in doc.items():
        if k in ALLOW_KEYS:
            if k == "주차별 강의진행계획서" and isinstance(v, dict):
                picked[k] = flatten_week_plan(v)
            else:
                picked[k] = str(v)
    if not picked:
        picked = {k: str(v) for k, v in doc.items() if k in ALLOW_KEYS}
    return picked


def preprocess(json_files: np.ndarray) -> list[str]:
    preprocessed = []
    for doc in json_files:
        selected = select_fields(doc)
        combined_text = " ".join(selected.values())
        preprocessed.append(combined_text)
    return preprocessed


if __name__ == "__main__":

    json_files = load_json_files("syllabus/json")
    # print(json_files)
    print(preprocess(json_files)[0])
