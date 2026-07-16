import psycopg2
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

conn = psycopg2.connect('postgresql://postgres:ilXBPGUbAKhmSqwQtTPxPsjslKepTsBg@mainline.proxy.rlwy.net:32180/railway')
cur = conn.cursor()

# 1. Check all tables
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
tables = cur.fetchall()
print('=== ALL TABLES ===')
for t in tables:
    print(t[0])

# 2. Check auto_responses for salam keywords
print('\n=== AUTO_RESPONSES with salam keyword ===')
cur.execute("SELECT id, keyword, response, is_active FROM auto_responses")
rows = cur.fetchall()
col_names = [desc[0] for desc in cur.description]
print(f'Columns: {col_names}')
for r in rows:
    print(r)

# 3. Check channel_groups for test link
print('\n=== CHANNEL_GROUPS (testinngngngng) ===')
cur.execute("SELECT id, title, invite_link, is_official FROM channel_groups WHERE invite_link LIKE '%testinngngngng%'")
rows = cur.fetchall()
for r in rows:
    print(r)

# 4. Show ALL channel_groups invite links
print('\n=== ALL CHANNEL_GROUPS ===')
cur.execute("SELECT id, title, invite_link, is_official FROM channel_groups")
rows = cur.fetchall()
col_names = [desc[0] for desc in cur.description]
print(f'Columns: {col_names}')
for r in rows:
    print(r)

# 5. Search ALL tables for testinngngngng
print('\n=== SEARCHING ALL TABLES for testinngngngng ===')
for t in tables:
    table = t[0]
    try:
        cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table,))
        cols = [row[0] for row in cur.fetchall()]
        for col in cols:
            try:
                cur.execute(f'SELECT * FROM "{table}" WHERE "{col}"::text LIKE %s', ('%testinngngngng%',))
                rows = cur.fetchall()
                if rows:
                    print(f'FOUND in {table}.{col}: {len(rows)} rows')
                    for r in rows:
                        print(r)
            except Exception as e2:
                pass
    except Exception as e:
        print(f'Error checking {table}: {e}')

conn.close()
print('\nDone.')
