# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import re, io
import pandas as pd

ENCODINGS = ["utf-8-sig", "gb18030", "gbk", "utf-8"]
SEPS = [",", "|", "\t", ";"]

def detect_file_type(path: Path) -> str:
    head = path.read_bytes()[:4]
    if head.startswith(b"\xD0\xCF\x11\xE0"):
        return "xls"
    if head.startswith(b"\x50\x4B\x03\x04"):
        return "xlsx"
    return "text"

def sniff_encoding_bytes(b: bytes) -> str:
    for enc in ENCODINGS:
        try:
            b.decode(enc); return enc
        except Exception:
            continue
    return "utf-8-sig"

def sniff_encoding(path: Path) -> str:
    head = path.read_bytes()[:65536]
    return sniff_encoding_bytes(head)

def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "").replace("，", ",").replace("｜", "|")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
    return text

def sniff_sep(text: str) -> str:
    head = "\n".join(text.splitlines()[:50])
    scores = {s: head.count(s) for s in SEPS}
    return max(scores, key=scores.get) if max(scores.values())>0 else r"\s+"

def read_any(path: str) -> pd.DataFrame:
    p = Path(path)
    ftype = detect_file_type(p)
    if ftype == "xls":
        return pd.read_excel(p, engine="xlrd")  # xlrd==1.2.0
    elif ftype == "xlsx":
        return pd.read_excel(p, engine="openpyxl")
    else:
        enc = sniff_encoding(p)
        raw = p.read_bytes()
        text = normalize_text(raw.decode(enc, errors="replace"))
        sep = sniff_sep(text)
        return pd.read_csv(io.StringIO(text), sep=sep if sep != r"\s+" else None, engine="python")

def to_two_decimals(s: str) -> str:
    try:
        v = float(str(s).replace(",", "").strip()); return f"{v:.2f}"
    except Exception:
        return str(s)

def is_empty(val) -> bool:
    if val is None: return True
    s = str(val).strip()
    return s == ""

def center_alignment_qt(table_widget):
    from PyQt5.QtCore import Qt
    for r in range(table_widget.rowCount()):
        for c in range(table_widget.columnCount()):
            item = table_widget.item(r, c)
            if item: item.setTextAlignment(Qt.AlignCenter)
