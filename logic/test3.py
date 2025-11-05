import shutil, os

folder = "logic/syllabus/normalized_json"
if os.path.exists(folder):
    shutil.rmtree(folder)
    print(f"🗑️ '{folder}' 폴더 및 내부 파일 전체 삭제 완료")
else:
    print(f"⚠️ '{folder}' 폴더가 존재하지 않습니다.")
