import psycopg2
import sys
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect("postgresql://postgres:evBwAxQqSyqvUEeEvqmiUPfkfAFdUOvR@hayabusa.proxy.rlwy.net:45938/railway")
cur = conn.cursor()

cur.execute("SELECT id, keyword, response, file_tg_id, file_url, file_type, news_id FROM auto_responses WHERE id = 428")
row = cur.fetchone()
if row:
    print(f"ID: {row[0]}")
    print(f"Keyword: {row[1]}")
    print(f"Response: {(row[2] or '')[:200]}")
    print(f"File TG ID: {row[3]}")
    print(f"File URL: {row[4]}")
    print(f"File Type: {row[5]}")
    print(f"News ID: {row[6]}")
else:
    print("Auto response 428 not found!")

cur.close()
conn.close()
