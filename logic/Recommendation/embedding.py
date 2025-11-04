from openai import OpenAI
import pandas as pd, os, ast, time
from preprocess import preprocess
from Utils import load_json_files

client = OpenAI()

csv_path = "embeddings.csv"
if os.path.exists(csv_path):
    df_existing = pd.read_csv(csv_path)
    df_existing["embedding"] = df_existing["embedding"].apply(ast.literal_eval)
    print(f"📂 기존 데이터 {len(df_existing)}개 불러옴")
else:
    df_existing = pd.DataFrame(columns=["text", "embedding"])
    print("⚠️ 기존 CSV 없음, 새로 생성")

json_files = load_json_files("syllabus/json")
preprocessed_texts = preprocess(json_files)
new_texts = [t for t in preprocessed_texts if t not in set(df_existing["text"])]

if not new_texts:
    print("✅ 모든 텍스트가 이미 저장되어 있습니다.")
else:
    BATCH_SIZE = 20  # 👈 한 번에 20개씩만 처리 (안전)
    new_embeddings = []

    for i in range(0, len(new_texts), BATCH_SIZE):
        batch = new_texts[i : i + BATCH_SIZE]
        print(f"🔹 임베딩 생성 중... {i+1} ~ {i+len(batch)} / {len(new_texts)}")

        res = client.embeddings.create(model="text-embedding-3-small", input=batch)
        batch_embeddings = [item.embedding for item in res.data]
        new_embeddings.extend(batch_embeddings)

        time.sleep(1)  # API rate limit 방지 (optional)

    df_new = pd.DataFrame({"text": new_texts, "embedding": new_embeddings})
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined.to_csv(csv_path, index=False)
    print(f"✅ 총 {len(df_combined)}개 임베딩이 '{csv_path}'에 저장되었습니다.")
