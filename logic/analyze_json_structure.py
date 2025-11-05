from pathlib import Path
import json

FOLDER = Path("logic/syllabus/json")  # 폴더 경로


def extract_keys(data, prefix=""):
    """JSON 내부 키 경로 추출 (중첩 딕셔너리도 지원)"""
    keys = set()
    if isinstance(data, dict):
        for k, v in data.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            keys.add(new_prefix)
            keys |= extract_keys(v, new_prefix)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            keys |= extract_keys(item, f"{prefix}[]")
    return keys


def analyze_json_structures(folder):
    structures = {}
    all_keys = set()

    for p in folder.glob("*.json"):
        try:
            with p.open(encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ {p.name} 불러오기 실패: {e}")
            continue

        keys = extract_keys(data)
        structures[p.name] = keys
        all_keys |= keys

    print("\n=== 전체 JSON 구조 비교 ===")
    all_keys = sorted(all_keys)
    for key in all_keys:
        present = [name for name, keys in structures.items() if key in keys]
        print(f"{key} → {len(present)}개 파일 존재")

    print("\n=== 파일별 누락된 키 ===")
    for name, keys in structures.items():
        missing = sorted(all_keys - keys)
        if missing:
            print(f"\n{name} 에서 누락된 키:")
            for m in missing:
                print("  -", m)


if __name__ == "__main__":
    analyze_json_structures(FOLDER)
