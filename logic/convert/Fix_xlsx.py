from openpyxl import load_workbook
import zipfile
import tempfile
import shutil
import os


def resave_excel_as_standard(file_path: str, output_path: str | None = None) -> str:
    """
    📘 비표준 또는 버전정보 누락 XLSX 파일을
    표준 엑셀(.xlsx) 형식으로 다시 저장하는 함수.

    Parameters
    ----------
    file_path : str
        원본 .xlsx 파일 경로
    output_path : str | None
        새로 저장할 파일 경로 (기본값: "_fixed" 붙임)

    Returns
    -------
    str : 저장된 새 파일 경로
    """
    if output_path is None:
        base, ext = os.path.splitext(file_path)
        output_path = f"fixed/{base}{ext}"

    try:
        wb = load_workbook(file_path, data_only=True)
        wb.save(output_path)
        print(f"✅ 재저장 완료: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ 재저장 실패: {e}")
        return ""


def fix_applynumberform_in_xlsx(file_path: str, output_path: str) -> str:
    """
    🧩 비표준 스타일 속성 'applyNumberForm'을 자동 수정하여
    정상적인 XLSX 파일로 복구하는 함수
    """
    try:
        # 임시 폴더 생성
        temp_dir = tempfile.mkdtemp()

        # ZIP 압축 해제
        with zipfile.ZipFile(file_path, "r") as z:
            z.extractall(temp_dir)

        # xl/styles.xml 수정
        style_path = os.path.join(temp_dir, "xl", "styles.xml")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8", errors="ignore") as f:
                xml_data = f.read()

            # 핵심 수정 부분
            xml_data = xml_data.replace("applyNumberForm", "applyNumberFormat")

            with open(style_path, "w", encoding="utf-8") as f:
                f.write(xml_data)
            print("✅ 'applyNumberForm' → 'applyNumberFormat' 수정 완료")
        else:
            print("⚠️ styles.xml이 존재하지 않음 (수정 불필요할 수 있음)")

        # 새 ZIP으로 다시 압축
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, temp_dir)
                    z.write(abs_path, rel_path)

        shutil.rmtree(temp_dir)
        print(f"✅ 복구 완료: {output_path}")
        return output_path

    except Exception as e:
        print(f"❌ 복구 실패: {e}")
        return ""


if __name__ == "__main__":
    # resave_excel_as_standard("logic/syllabus/report (3).xlsx")
    fix_applynumberform_in_xlsx(
        "logic/syllabus/report.xlsx", "logic/syllabus/report_fixed.xlsx"
    )
