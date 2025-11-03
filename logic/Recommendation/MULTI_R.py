from Utils import load_json_files, tfidf_similarity, bert_similarity, preprocess_json
import numpy as np

folder_path = "logic/syllabus/json"
json_files = load_json_files(folder_path)  # list[dict]
data = preprocess_json(json_files)  # np.ndarray[str], 원본과 같은 순서 가정

# 원본 인덱스 매핑 배열
orig_idx = np.arange(len(data))

# 1) 사용자 수강 리스트 통합
user_idx = np.array([1, 2, 3, 4, 5, 6, 7])
print([d["교과목명"] for d in json_files[user_idx]])
user_text = " ".join(data[user_idx])
print(user_text)

# 2) data/매핑 동시 삭제 후, 유저 프로필 추가
data = np.delete(data, user_idx, axis=0)
orig_idx = np.delete(orig_idx, user_idx, axis=0)
data = np.concatenate([data, np.array([user_text])])
orig_idx = np.concatenate([orig_idx, np.array([-1])])  # -1 = 유저 프로필 표시

# 3) TF-IDF 상위 후보
sim_tfidf = tfidf_similarity(data)
user_pos = len(data) - 1
top_indices = np.argsort(sim_tfidf[user_pos])[-100:]
top_indices = np.unique(np.append(top_indices, user_pos))

# 4) BERT 유사도 (후보만)
sim_bert = bert_similarity(data[top_indices])

# 기준 문서 위치(후보 집합 내)
center_idx = np.where(top_indices == user_pos)[0][0]

# 5) 상위 N개 (자기 자신 제외)
top_n = 10
order = np.argsort(sim_bert[center_idx])[::-1]  # 내림차순
order = order[sim_bert[center_idx][order] < 0.999999]  # self 제거
top_local = order[:top_n]

print("==== Top 10 Similar Courses ====")
for loc in top_local:
    cur_pos = top_indices[loc]  # data 기준 인덱스
    src_idx = orig_idx[cur_pos]  # 원본 json_files 인덱스(-1이면 유저 프로필)
    name = "USER_PROFILE" if src_idx == -1 else json_files[src_idx]["교과목명"]
    print(f"{name:<30} | sim = {sim_bert[center_idx][loc]:.3f}")
