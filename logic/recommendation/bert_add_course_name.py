# ===============================
# BERT 임베딩 생성 및 저장 (get 방식)
# ===============================
from sentence_transformers import SentenceTransformer
import pandas as pd, numpy as np, ast, os
from Utils import load_json_files, preprocess_json


def generate_and_save_embeddings(
    json_folder="logic/syllabus/json", save_path="logic/results/bert_embeddings.csv"
):
    # 1. 데이터 불러오기
    json_files = load_json_files(json_folder)
    data = preprocess_json(json_files)  # 임베딩 텍스트

    # get()으로 안전하게 접근
    course_names = [d.get("교과목명", "") for d in json_files]
    course_ids = [d.get("학수번호", "") for d in json_files]
    sections = [d.get("분반", "") for d in json_files]

    # 2. BERT 임베딩
    model = SentenceTransformer(
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    embeddings = model.encode(data, normalize_embeddings=True)

    # 3. DataFrame 저장
    df = pd.DataFrame(
        {
            "교과목명": course_names,
            "학수번호": course_ids,
            "분반": sections,
            "embedding": [emb.tolist() for emb in embeddings],
        }
    )

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    df.to_csv(save_path, index=False, encoding="utf-8-sig")

    print(f"✅ 저장 완료: {save_path} ({len(df)}개 과목)")


if __name__ == "__main__":
    generate_and_save_embeddings()
