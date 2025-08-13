# -*- coding: utf-8 -*-
from __future__ import annotations
import re, sqlite3
import pandas as pd
from .common_import import read_any, is_empty

EXPECTED = ["BNKCODE","CLSCODE","CITYCODE","LNAME"]

def normalize_bankcodes(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("文件为空或无数据")
    cols = [str(c).strip().upper().lstrip("\ufeff") for c in df.columns]
    df.columns = cols
    if len(df.columns) < 4:
        raise ValueError("表头不匹配，期望列：BNKCODE, CLSCODE, CITYCODE, LNAME")
    df = df.iloc[:, :4].copy()
    df.columns = EXPECTED
    for c in EXPECTED:
        df[c] = df[c].astype(str).str.strip()
    df = df[~(df == "").all(axis=1)]
    errs = []
    for i, r in df.iterrows():
        rown = i + 1
        if not re.fullmatch(r"\d{12}", r["BNKCODE"] or ""):
            errs.append(f"第{rown}行 | 字段[BNKCODE] | 原值“{r['BNKCODE']}” | 错因：必须为12位数字")
        if not re.fullmatch(r"\d{3}", r["CLSCODE"] or ""):
            errs.append(f"第{rown}行 | 字段[CLSCODE] | 原值“{r['CLSCODE']}” | 错因：必须为3位数字")
        if not re.fullmatch(r"\d{4}", r["CITYCODE"] or ""):
            errs.append(f"第{rown}行 | 字段[CITYCODE] | 原值“{r['CITYCODE']}” | 错因：必须为4位数字")
        if is_empty(r["LNAME"]):
            errs.append(f"第{rown}行 | 字段[LNAME] | 原值“{r['LNAME']}” | 错因：必填但为空")
    if errs:
        sample = "\n".join(errs[:20])
        more = f"\n… 其余 {len(errs)-20} 条未列出" if len(errs) > 20 else ""
        raise ValueError(sample + more)
    return df

def upsert_sqlite(df: pd.DataFrame, db_path: str, table: str):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table}(
            BNKCODE  TEXT PRIMARY KEY,
            CLSCODE  TEXT NOT NULL,
            CITYCODE TEXT NOT NULL,
            LNAME    TEXT NOT NULL
        );
    """)
    cur.executemany(
        f"""INSERT INTO {table}(BNKCODE,CLSCODE,CITYCODE,LNAME)
            VALUES (?,?,?,?)
            ON CONFLICT(BNKCODE) DO UPDATE SET
                CLSCODE=excluded.CLSCODE,
                CITYCODE=excluded.CITYCODE,
                LNAME=excluded.LNAME;""",
        df[EXPECTED].values.tolist()
    )
    conn.commit(); conn.close()

def import_bankcodes(path: str, db_path: str, src: str = "IBPS"):
    df = read_any(path)
    df = normalize_bankcodes(df)
    table = "bank_codes_ibps" if src.upper()=="IBPS" else "bank_codes_cnaps"
    upsert_sqlite(df, db_path, table)
    return len(df)
