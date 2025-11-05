from pathlib import Path
import json
import re

FOLDER = Path("logic/syllabus/json")  # 필요시 경로 수정


def sanitize(s: str) -> str:
    # 파일명에 쓸 수 없는 문자 제거
    return re.sub(r'[\\/:*?"<>|]', "_", s).strip()


def rename_all(folder: Path):
    count_ok, count_skip, count_err = 0, 0, 0
    for p in sorted(folder.glob("*.json")):
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ 읽기 실패: {p.name} -> {e}")
            count_err += 1
            continue

        course = str(data.get("학수번호", "")).strip()
        section = str(data.get("분반", "")).strip()

        if not course or not section:
            print(
                f"⚠️ 필드 누락으로 건너뜀: {p.name} (학수번호='{course}', 분반='{section}')"
            )
            count_skip += 1
            continue

        # 필요하면 분반 3자리 패딩 사용: section = section.zfill(3)
        section = section.zfill(3)
        new_name = f"{sanitize(course)}-{sanitize(section)}.json"
        target = p.with_name(new_name)

        if target == p:
            print(f"= 이미 원하는 이름: {p.name}")
            count_skip += 1
            continue

        # 이름 충돌 시 뒤에 -1, -2... 붙이기
        if target.exists():
            i = 1
            while True:
                alt = p.with_name(target.stem + f"-{i}" + target.suffix)
                if not alt.exists():
                    target = alt
                    break
                i += 1

        try:
            p.rename(target)
            print(f"✅ {p.name} -> {target.name}")
            count_ok += 1
        except Exception as e:
            print(f"❌ 변경 실패: {p.name} -> {target.name} ({e})")
            count_err += 1

    print(f"\n완료: 변경 {count_ok}건 | 건너뜀 {count_skip}건 | 오류 {count_err}건")


if __name__ == "__main__":
    rename_all(FOLDER)
