from Utils import load_json_files, preprocess_json
import numpy as np

if __name__ == "__main__":
    folder_path = "logic/syllabus/json"
    json_files = load_json_files(folder_path)
    # print([d["교과목명"] for d in json_files[:2]])

    data = preprocess_json(json_files)

    # 1️⃣ TF-IDF로 1차 후보군 좁히기
    sim_tfidf = tfidf_similarity(data)

    # 예: 유사도 상위 100개만 선택
    user_idx = 1  # 비교할 문서 인덱스 설정
    top_indices = np.argsort(sim_tfidf[user_idx])[-100:]
    top_indices = np.append(top_indices, user_idx)
    top_indices = np.unique(top_indices)  # 중복 제거

    # 2️⃣ BERT 임베딩은 top-100만 계산
    sim_bert = bert_similarity(data[top_indices])

    # 3️⃣ 기준 문서의 위치 찾기
    center_idx = np.where(top_indices == user_idx)[0][0]

    top_n = 10
    top_local = np.argsort(sim_bert[center_idx])[-top_n:][::-1]
    print("==== Top 10 Similar Courses ====")
    for idx in top_local:
        course_idx = top_indices[idx]
        print(
            f"{json_files[course_idx]['교과목명']:<30} | sim = {sim_bert[center_idx][idx]:.3f}"
        )
