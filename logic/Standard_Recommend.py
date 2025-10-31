import mysql.connector

# 1️⃣ DB 연결
conn = mysql.connector.connect(
    host="localhost",       # DB 서버 주소
    user="root",            # 사용자명
    password="비밀번호",
    database="testdb"       # 사용할 DB 이름
)

# 2️⃣ 커서(cursor) 생성
cursor = conn.cursor()

# 3️⃣ SQL 실행
cursor.execute("SELECT * FROM users;")

# 4️⃣ 결과 가져오기
rows = cursor.fetchall()

for row in rows:
    print(row)

# 5️⃣ 연결 종료
cursor.close()
conn.close()
