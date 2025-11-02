from bs4 import BeautifulSoup
import re
import json
import os


def html_to_json(file_path: str, output_path: str = None) -> dict:
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    result = {}

    # ---------------------------
    # 1️⃣ Table1: 기본정보
    # ---------------------------
    table1 = soup.find(id="Table1")
    if table1:
        text = table1.get_text(" ", strip=True)
        info = {}
        # 정규식 예시 (학수번호-분반)
        m = re.search(r"([A-Z]+[0-9]+-\d+)", text)
        if m:
            info["학수번호"] = m.group(1)
        # 과목명 / 교수명
        subj = re.search(r"교과목명[:：]?\s*([\w\s\(\)\/]+)", text)
        if subj:
            info["교과목명"] = subj.group(1).strip()
        prof = re.search(r"교수명[:：]?\s*([\w가-힣\s]+)", text)
        if prof:
            info["담당교수"] = prof.group(1).strip()
        result["교과목기본정보"] = info

    # ---------------------------
    # 2️⃣ Table2: 주차별 강의계획
    # ---------------------------
    weekly_plan = {}
    table2 = soup.find(id="Table2")
    if table2:
        rows = table2.find_all("tr")
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if len(cols) >= 3 and re.match(r"^\d+$", cols[0]):
                week = f"{int(cols[0])}주차"
                weekly_plan[week] = {"주제": cols[1], "강의내용": cols[2:]}

    if weekly_plan:
        result["주차별강의계획"] = weekly_plan

    # ---------------------------
    # 3️⃣ Table3: 평가 / 교재 정보
    # ---------------------------
    table3 = soup.find(id="Table3")
    if table3:
        text = table3.get_text(" ", strip=True)
        grading = {}
        for key in ["중간", "기말", "과제", "출석", "기타"]:
            m = re.search(rf"{key}[^0-9]*([\d]+)", text)
            if m:
                grading[key] = int(m.group(1))
        if grading:
            result["평가기준"] = grading

        # 교재
        book = re.search(r"교재명[:：]?\s*([^\n]+)", text)
        if book:
            result["교재"] = book.group(1).strip()

    # ---------------------------
    # 4️⃣ Table4: 운영방식 등
    # ---------------------------
    table4 = soup.find(id="Table4")
    if table4:
        text = table4.get_text(" ", strip=True)
        result["운영방식"] = text

    # ---------------------------
    # 5️⃣ script 내 평가비율(txtPyeongga)
    # ---------------------------
    scripts = soup.find_all("script")
    for s in scripts:
        if "txtPyeongga" in s.text:
            matches = re.findall(r"txtPyeongga\d+\s*=\s*'(\d+)'", s.text)
            if matches:
                result.setdefault("평가기준", {})
                for i, val in enumerate(matches, 1):
                    result["평가기준"][f"항목{i}"] = int(val)

    # ---------------------------
    # 6️⃣ JSON 저장
    # ---------------------------
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 저장 완료 → {output_path}")

    return result


if __name__ == "__main__":
    html_dir = "logic/syllabus/html"
    json_dir = "logic/syllabus/json"

    os.makedirs(json_dir, exist_ok=True)

    for file in os.listdir(html_dir):
        if file.endswith(".html"):
            src = os.path.join(html_dir, file)
            dst = os.path.join(json_dir, os.path.splitext(file)[0] + ".json")
            print(f"📘 변환 중: {src}")
            html_to_json(src, dst)
            break
