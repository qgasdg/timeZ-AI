import os
import sys
import json
from pathlib import Path

import pandas as pd


def read_excel_auto(path: Path):
    """확장자에 맞춰 엔진 자동 선택해서 모든 시트를 dict[str, DataFrame]으로 반환"""
    ext = path.suffix.lower()
    if ext == ".xlsx":
        # .xlsx → openpyxl
        return pd.read_excel(path, sheet_name=None, engine="openpyxl")
    elif ext == ".xls":
        # .xls → xlrd  (xlrd가 설치되어 있어야 함)
        return pd.read_excel(path, sheet_name=None, engine="xlrd")
    else:
        raise ValueError(f"지원하지 않는 확장자: {ext} ({path.name})")


def excel_dir_to_json(input_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)

    excel_files = [p for p in input_dir.iterdir()
                   if p.is_file() and p.suffix.lower() in (".xls", ".xlsx")]

    if not excel_files:
        print(f"❌ 엑셀 파일이 없습니다: {input_dir}")
        return

    print(f"📂 입력 폴더: {input_dir.resolve()}")
    print(f"💾 출력 폴더: {out_dir.resolve()}")
    print(f"🔎 파일 개수: {len(excel_files)}\n")

    for fpath in excel_files:
        print(f"📘 처리 중: {fpath.name}")
        try:
            sheets = read_excel_auto(fpath)
            for sheet_name, df in (sheets or {}).items():
                df = df.fillna("")  # NaN → 빈문자
                records = df.to_dict(orient="records")

                base = fpath.stem
                safe_sheet = "".join(ch if str(ch).isalnum() else "_" for ch in str(sheet_name))
                out_file = out_dir / f"{base}_{safe_sheet}.json"

                with open(out_file, "w", encoding="utf-8") as fw:
                    json.dump(records, fw, ensure_ascii=False, indent=2, default=str)

                print(f"  → 저장: {out_file.name} ({len(records)}행)")
        except Exception as e:
            print(f"  ⚠️ 실패: {fpath.name} - {e}")
        print()

    print("✅ 변환 완료!")


if __name__ == "__main__":
    # 실행 위치에 상관없이 동작하도록 기준 경로를 스크립트 위치로 고정
    script_dir = Path(__file__).parent

    # 인자: 입력폴더, 출력폴더 (미지정시 기본값 사용)
    input_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else (script_dir / "test_data")
    out_dir   = Path(sys.argv[2]) if len(sys.argv) > 2 else (script_dir / "test_json_output")

    # 존재 확인 및 친절한 안내
    if not input_dir.exists():
        print(f"❌ 입력 폴더가 없습니다: {input_dir.resolve()}")
        print("   → 올바른 경로를 첫 번째 인자로 넘기거나, Y/test_data 폴더를 만들어주세요.")
        sys.exit(1)
    

    excel_dir_to_json(input_dir, out_dir)

