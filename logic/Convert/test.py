import pandas as pd

df = pd.read_csv("syllabus_merged.csv", nrows=0)
print(df.columns.tolist())
