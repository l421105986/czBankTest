# -*- coding: utf-8 -*-
import sqlite3

def ensure_db(path: str):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.close()

def query_bankcodes(db_path: str, table: str, keyword: str = "", limit: int = 200):
    conn = sqlite3.connect(db_path)
    kw = f"%{keyword}%"
    cur = conn.cursor()
    cur.execute(f"""
        SELECT BNKCODE, CLSCODE, CITYCODE, LNAME
        FROM {table}
        WHERE BNKCODE LIKE ? OR LNAME LIKE ?
        ORDER BY BNKCODE
        LIMIT ?
    """, (kw, kw, limit))
    rows = cur.fetchall()
    conn.close()
    return rows
