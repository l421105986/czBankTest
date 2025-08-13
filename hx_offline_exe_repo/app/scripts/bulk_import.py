# -*- coding: utf-8 -*-
from __future__ import annotations
import re
import pandas as pd
from .common_import import read_any, is_empty, to_two_decimals

EXPECTED = ["NAME","ACCT","AMOUNT","BANKNAME","BNKCODE","LINE_TYPE"]

def normalize_bulk(df: pd.DataFrame, source_hint: str|None=None) -> pd.DataFrame:
    if df is None or df.empty:
        raise ValueError("文件为空或无数据")
    cols = [str(c).strip().upper().lstrip("\ufeff") for c in df.columns]
    df.columns = cols
    if len(df.columns) < 6:
        df = df.reindex(columns=df.columns.tolist() + ["X"]*(6-len(df.columns)))
    df = df.iloc[:, :6].copy()
    df.columns = EXPECTED
    for c in EXPECTED:
        df[c] = df[c].astype(str).str.strip()
    df = df[~(df == "").all(axis=1)]
    errs = []
    for i, r in df.iterrows():
        rown = i + 1
        name, acct, amt, bank, code, lt = r["NAME"], r["ACCT"], r["AMOUNT"], r["BANKNAME"], r["BNKCODE"], r["LINE_TYPE"]
        if is_empty(name): errs.append(f"第{rown}行 | 字段[NAME] | 原值“{name}” | 错因：必填但为空")
        elif len(name) > 64: errs.append(f"第{rown}行 | 字段[NAME] | 原值“{name}” | 错因：长度超限(>64)")
        if not re.fullmatch(r"\d{8,32}", acct or ""):
            errs.append(f"第{rown}行 | 字段[ACCT] | 原值“{acct}” | 错因：仅数字且长度8–32")
        try:
            v = float(str(amt).replace(",", ""))
            if v <= 0: errs.append(f"第{rown}行 | 字段[AMOUNT] | 原值“{amt}” | 错因：金额必须>0")
        except Exception:
            errs.append(f"第{rown}行 | 字段[AMOUNT] | 原值“{amt}” | 错因：无法解析为金额")
        if is_empty(bank): errs.append(f"第{rown}行 | 字段[BANKNAME] | 原值“{bank}” | 错因：必填但为空")
        elif len(bank) > 128: errs.append(f"第{rown}行 | 字段[BANKNAME] | 原值“{bank}” | 错因：长度超限(>128)")
        if code and not re.fullmatch(r"\d{12}", code):
            errs.append(f"第{rown}行 | 字段[BNKCODE] | 原值“{code}” | 错因：非12位数字或包含非数字字符")
        if lt and lt not in ("清算","大额"):
            errs.append(f"第{rown}行 | 字段[LINE_TYPE] | 原值“{lt}” | 错因：仅允许 清算/大额")
    if errs:
        sample = "\n".join(errs[:20]); more = f"\n… 其余 {len(errs)-20} 条未列出" if len(errs) > 20 else ""
        raise ValueError(sample + more)
    df["AMOUNT"] = df["AMOUNT"].map(to_two_decimals)
    # 含“华夏银行” → 行别空；转账方式UI端设为0-行内（导出收口也置空）
    def _apply(row):
        if "华夏银行" in (row.get("BANKNAME") or ""):
            row["LINE_TYPE"] = ""
        return row
    return df.apply(_apply, axis=1)
