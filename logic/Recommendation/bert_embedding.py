# ===============================
# 전체 강의 BERT 임베딩 → CSV 저장
# ===============================
from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
import ast, os
from Utils import load_json_files, preprocess_json


def create_bert_embeddings_csv(
    folder_path="logic/syllabus/json",
    output_csv="logic/results/bert_embeddings.csv",
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    batch_size=32,
):
    # 1. JSON 불러오기
    json_files = load_json_files(folder_path)
    data = preprocess_json(json_files)
    print(f"📂 총 {len(data)}개 문서 로드 완료")
    print(data[:2])  # 샘플 출력

    # 2. 모델 로드
    model = SentenceTransformer(model_name)

    # 3. 배치 단위 임베딩 계산
    all_embeddings = []
    for i in range(0, len(data), batch_size):
        batch_texts = data[i : i + batch_size]
        batch_embeddings = model.encode(batch_texts, normalize_embeddings=True)
        all_embeddings.extend(batch_embeddings)
        print(f"✅ {i+len(batch_texts)}/{len(data)}개 임베딩 완료")

    # 4. DataFrame 구성
    df = pd.DataFrame(
        {
            "학수번호": [d.get("학수번호", None) for d in json_files],
            "분반": [d.get("분반", None) for d in json_files],
            "embedding": [emb.tolist() for emb in all_embeddings],
        }
    )

    # 5. 저장
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"💾 임베딩 CSV 저장 완료 → {output_csv}")

    return df


# -------------------------------
# 실행 예시
# -------------------------------
if __name__ == "__main__":
    df = create_bert_embeddings_csv()
