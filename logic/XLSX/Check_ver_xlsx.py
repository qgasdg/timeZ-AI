import zipfile
from xml.etree import ElementTree as ET

def get_excel_version(file_path):
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            with z.open('docProps/app.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                for elem in root:
                    if "AppVersion" in elem.tag:
                        print(f"📘 Excel 버전: {elem.text}")
                        return elem.text
        print("⚠️ 버전 정보를 찾을 수 없습니다 (일부 파일은 이 필드 없음).")
    except Exception as e:
        print(f"❌ 엑셀 파일을 읽을 수 없습니다: {e}")

def inspect_excel_structure(file_path: str):
    """
    엑셀 파일(.xlsx)의 내부 ZIP 구조를 검사하여
    - 정상 Excel 구조인지
    - docProps/app.xml(버전 정보)이 존재하는지
    - 손상 또는 비표준 포맷인지
    를 진단해주는 함수
    """
    result = {"파일": file_path}

    # ZIP 파일인지 확인
    if not zipfile.is_zipfile(file_path):
        result["상태"] = "❌ ZIP 구조 아님 (실제로는 .xls 또는 비표준 형식)"
        return result

    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            names = z.namelist()
            result["내부파일수"] = len(names) # type: ignore
            result["xl/workbook.xml"] = "✅ 존재" if "xl/workbook.xml" in names else "⚠️ 없음"
            result["docProps/app.xml"] = "✅ 존재" if "docProps/app.xml" in names else "⚠️ 없음"

            # 최종 판단
            if "xl/workbook.xml" not in names:
                result["상태"] = "⚠️ 비표준 XLSX (xl/workbook.xml 없음)"
            elif "docProps/app.xml" not in names:
                result["상태"] = "⚠️ 버전정보 누락 XLSX (docProps/app.xml 없음)"
            else:
                result["상태"] = "✅ 정상 XLSX 구조"

    except Exception as e:
        result["상태"] = f"❌ ZIP 읽기 오류: {e}"

    return result

# 예시
if __name__ == "__main__":
    # get_excel_version("logic/syllabus/report (3).xlsx")
    get_excel_version("logic/syllabus/report.xlsx")
    # get_excel_version("logic/syllabus/report_fixed.xlsx")
    # get_excel_version("logic/syllabus/report_xls.xls")

    path = "logic/syllabus/report.xlsx"
    # path = "logic/syllabus/report_xls.xls"
    info = inspect_excel_structure(path)
    for k, v in info.items():
        print(f"{k}: {v}")
