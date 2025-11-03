import json
from Recommendation.Utils import load_json_files
import os

file_path = "logic/syllabus/json"

counter = 0
for file in os.listdir(file_path):
    if file.endswith(".json"):
        counter += 1
        if counter == 223:
            print(file)
