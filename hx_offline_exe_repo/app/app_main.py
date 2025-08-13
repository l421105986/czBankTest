# -*- coding: utf-8 -*-
import sys, os
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QWidget, QFileDialog, QMessageBox, QVBoxLayout, QHBoxLayout,
    QPushButton, QTabWidget, QRadioButton, QLineEdit, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QComboBox, QAbstractItemView, QDialog, QGridLayout)
from PyQt5.QtCore import Qt
import pandas as pd

from scripts.common_import import center_alignment_qt, is_empty
from scripts.bankcodes_import import import_bankcodes
from scripts.db_helpers import ensure_db, query_bankcodes
from scripts.common_import import read_any
from scripts.payroll_import import normalize_payroll
from scripts.bulk_import import normalize_bulk

APP_DIR = Path(__file__).parent
DATA_DB = str(APP_DIR / "data" / "app.db")

class BankPicker(QDialog):
    def __init__(self, parent=None, src="IBPS"):
        super().__init__(parent)
        self.setWindowTitle("选择行号")
        self.resize(700, 480)
        self.src = src
        lay = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("来源："))
        self.cmb = QComboBox(); self.cmb.addItems(["IBPS(清算)","CNAPS(大额)"])
        if src=="CNAPS": self.cmb.setCurrentIndex(1)
        bar.addWidget(self.cmb)
        bar.addWidget(QLabel("关键词："))
        self.kw = QLineEdit(); bar.addWidget(self.kw)
        btn = QPushButton("查询"); btn.clicked.connect(self.do_query)
        bar.addWidget(btn)
        lay.addLayout(bar)
        self.table = QTableWidget(0,4); self.table.setHorizontalHeaderLabels(["BNKCODE","CLSCODE","CITYCODE","LNAME"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.accept)
        lay.addWidget(self.table)
        self.row = None
        self.do_query()
    def do_query(self):
        table = "bank_codes_ibps" if self.cmb.currentIndex()==0 else "bank_codes_cnaps"
        rows = query_bankcodes(DATA_DB, table, self.kw.text().strip(), 500)
        self.table.setRowCount(0)
        for r in rows:
            rowi = self.table.rowCount(); self.table.insertRow(rowi)
            for c,val in enumerate(r):
                self.table.setItem(rowi,c,QTableWidgetItem(str(val)))
        center_alignment_qt(self.table)
    def accept(self):
        i = self.table.currentRow()
        if i<0: return
        self.row = { "BNKCODE": self.table.item(i,0).text(),
                     "CLSCODE": self.table.item(i,1).text(),
                     "CITYCODE": self.table.item(i,2).text(),
                     "LNAME": self.table.item(i,3).text(),
                     "TYPE": "清算" if self.cmb.currentIndex()==0 else "大额" }
        super().accept()

class TabLibrary(QWidget):
    def __init__(self):
        super().__init__()
        self.src = "IBPS"
        lay = QVBoxLayout(self)
        top = QHBoxLayout()
        self.r1 = QRadioButton("IBPS（清算行号）"); self.r2 = QRadioButton("CNAPS（大额行号）")
        self.r1.setChecked(True)
        top.addWidget(self.r1); top.addWidget(self.r2); top.addStretch(1)
        self.btnImport = QPushButton("导入"); self.btnExport = QPushButton("导出库")
        top.addWidget(self.btnImport); top.addWidget(self.btnExport)
        top.addWidget(QLabel("关键词")); self.kw = QLineEdit(); top.addWidget(self.kw)
        lay.addLayout(top)

        self.table = QTableWidget(0,4); self.table.setHorizontalHeaderLabels(["BNKCODE","CLSCODE","CITYCODE","LNAME"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        lay.addWidget(self.table)

        self.r1.toggled.connect(lambda: self._set_src("IBPS" if self.r1.isChecked() else "CNAPS"))
        self.btnImport.clicked.connect(self.do_import)
        self.btnExport.clicked.connect(self.do_export)
        self.kw.textChanged.connect(self.refresh)

        self.refresh()

    def _set_src(self, s): self.src=s; self.refresh()

    def do_import(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择行号文件", "", "All (*);;Text/Excel (*.txt *.xls *.xlsx)")
        if not f: return
        try:
            n = import_bankcodes(f, DATA_DB, self.src)
            QMessageBox.information(self, "导入成功", f"成功导入 {n} 条到 {self.src} 库。")
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def refresh(self):
        table = "bank_codes_ibps" if self.src=="IBPS" else "bank_codes_cnaps"
        rows = query_bankcodes(DATA_DB, table, self.kw.text().strip(), 1000)
        self.table.setRowCount(0)
        for r in rows:
            i = self.table.rowCount(); self.table.insertRow(i)
            for c,val in enumerate(r):
                self.table.setItem(i,c,QTableWidgetItem(str(val)))
        center_alignment_qt(self.table)

    def do_export(self):
        table = "bank_codes_ibps" if self.src=="IBPS" else "bank_codes_cnaps"
        rows = query_bankcodes(DATA_DB, table, self.kw.text().strip(), 1000000)
        if not rows:
            QMessageBox.information(self,"导出库","当前库为空。"); return
        df = pd.DataFrame(rows, columns=["BNKCODE","CLSCODE","CITYCODE","LNAME"])
        sfx = "LCH" if self.src=="IBPS" else "CNAPS"
        f, _ = QFileDialog.getSaveFileName(self,"保存为","{}_EXPORT.csv".format(sfx),"CSV (*.csv)")
        if not f: return
        df.to_csv(f, index=False, encoding="utf-8-sig")
        QMessageBox.information(self,"导出库","导出完成。")

class BaseDataTab(QWidget):
    def __init__(self, title_cols):
        super().__init__()
        self.cols = title_cols
        lay = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.btnAdd = QPushButton("新增一条"); self.btnEdit = QPushButton("编辑选中")
        self.btnDel = QPushButton("删除选中"); self.btnImport = QPushButton("导入…（检验）")
        self.btnExport = QPushButton("校验并导出")
        bar.addWidget(self.btnAdd); bar.addWidget(self.btnEdit); bar.addWidget(self.btnDel)
        bar.addStretch(1); bar.addWidget(self.btnImport); bar.addWidget(self.btnExport)
        lay.addLayout(bar)

        self.table = QTableWidget(0, len(self.cols)); self.table.setHorizontalHeaderLabels(self.cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        lay.addWidget(self.table)

        self.btnAdd.clicked.connect(self.add_row)
        self.btnDel.clicked.connect(self.del_rows)

    def add_row(self):
        r = self.table.rowCount(); self.table.insertRow(r)
        for c in range(self.table.columnCount()):
            self.table.setItem(r, c, QTableWidgetItem(""))
        center_alignment_qt(self.table)

    def del_rows(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows: self.table.removeRow(r)

    def load_df(self, df: pd.DataFrame):
        self.table.setRowCount(0)
        for _, row in df.iterrows():
            r = self.table.rowCount(); self.table.insertRow(r)
            for c,col in enumerate(self.cols):
                self.table.setItem(r, c, QTableWidgetItem(str(row.get(col,""))))
        center_alignment_qt(self.table)

    def to_df(self) -> pd.DataFrame:
        data = []
        for r in range(self.table.rowCount()):
            data.append({ self.cols[c]: (self.table.item(r,c).text() if self.table.item(r,c) else "") for c in range(len(self.cols)) })
        return pd.DataFrame(data)

class TabPayroll(BaseDataTab):
    def __init__(self):
        super().__init__(["SEQ","NAME","ACCT","AMOUNT","BANKNAME","REMARK"])
        self.btnImport.setText("导入待发工资表（检验）")
        self.btnImport.clicked.connect(self.do_import)
        self.btnExport.clicked.connect(self.do_export)

    def do_import(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择代发工资文件", "", "All (*);;Text/Excel (*.txt *.xls *.xlsx)")
        if not f: return
        try:
            df = read_any(f)
            df = normalize_payroll(df)
            self.load_df(df)
            QMessageBox.information(self,"导入成功","格式校验通过，已加载到编辑区。")
        except Exception as e:
            QMessageBox.critical(self,"导入失败", str(e))

    def do_export(self):
        # 二次校验
        df = self.to_df()
        try:
            df = normalize_payroll(df)  # 直接复用校验
        except Exception as e:
            QMessageBox.critical(self,"导出前校验失败", str(e)); return
        f, _ = QFileDialog.getSaveFileName(self,"保存为","PAYROLL.csv","CSV (*.csv)")
        if not f: return
        df.to_csv(f, index=False, encoding="utf-8-sig")
        QMessageBox.information(self,"导出完成","已导出。")

class TabBulk(BaseDataTab):
    def __init__(self):
        super().__init__(["NAME","ACCT","AMOUNT","BANKNAME","BNKCODE","LINE_TYPE","TRANSFER_MODE"])
        self.btnImport.setText("导入批量转账表（检验）")
        self.btnImport.clicked.connect(self.do_import)
        self.btnExport.clicked.connect(self.do_export)

        # 默认下拉值参考：""/0-行内转账/1-跨行清算/2-跨行大额 —— 这里用文本列 TRANSFER_MODE 承载
        self.btnPick = QPushButton("为选中行选择行号")
        self.layout().itemAt(0).layout().addWidget(self.btnPick)
        self.btnPick.clicked.connect(self.pick_for_selected)

    def pick_for_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self,"选择行号","请先选择一行数据。"); return
        dlg = BankPicker(self, "IBPS")
        if dlg.exec_() == QDialog.Accepted:
            rec = dlg.row
            r = rows[0]
            self.table.setItem(r, 3, QTableWidgetItem(rec["LNAME"]))   # BANKNAME
            self.table.setItem(r, 4, QTableWidgetItem(rec["BNKCODE"])) # BNKCODE
            # 联动规则：含华夏银行 → TRANSFER_MODE=0-行内；LINE_TYPE=""
            if "华夏银行" in rec["LNAME"]:
                self.table.setItem(r, 6, QTableWidgetItem("0-行内转账"))
                self.table.setItem(r, 5, QTableWidgetItem(""))
            else:
                # 非华夏：按来源置 1/2
                self.table.setItem(r, 6, QTableWidgetItem("1-跨行清算" if rec["TYPE"]=="清算" else "2-跨行大额"))
            center_alignment_qt(self.table)

    def do_import(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择批量转账文件", "", "All (*);;Text/Excel (*.txt *.xls *.xlsx)")
        if not f: return
        try:
            df = read_any(f)
            df = normalize_bulk(df)
            # 补上 TRANSFER_MODE 列（规则：含华夏→0-行内；否则默认1-跨行，用户可改）
            df["TRANSFER_MODE"] = df["BANKNAME"].map(lambda s: "0-行内转账" if "华夏银行" in str(s) else "1-跨行清算")
            self.load_df(df[["NAME","ACCT","AMOUNT","BANKNAME","BNKCODE","LINE_TYPE","TRANSFER_MODE"]])
            QMessageBox.information(self,"导入成功","格式校验通过，已加载到编辑区。")
        except Exception as e:
            QMessageBox.critical(self,"导入失败", str(e))

    def do_export(self):
        df = self.to_df()
        # 收口：凡 TRANSFER_MODE 以 0- 开头 → LINE_TYPE 置空
        df.loc[df["TRANSFER_MODE"].fillna("").str.startswith("0-"), "LINE_TYPE"] = ""
        # 二次校验（不校验 TRANSFER_MODE 文案）
        try:
            _ = normalize_bulk(df[["NAME","ACCT","AMOUNT","BANKNAME","BNKCODE","LINE_TYPE"]])
        except Exception as e:
            QMessageBox.critical(self,"导出前校验失败", str(e)); return
        # 导出
        f, _ = QFileDialog.getSaveFileName(self,"保存为","BULK.csv","CSV (*.csv)")
        if not f: return
        df.to_csv(f, index=False, encoding="utf-8-sig")
        QMessageBox.information(self,"导出完成","已导出。")

class MainWin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("业务工具（确认版）")
        self.resize(1000, 680)
        ensure_db(DATA_DB)
        lay = QVBoxLayout(self)
        tabs = QTabWidget(); lay.addWidget(tabs)
        self.tabLib = TabLibrary(); tabs.addTab(self.tabLib, "库维护")
        self.tabPay = TabPayroll(); tabs.addTab(self.tabPay, "代发工资")
        self.tabBulk = TabBulk(); tabs.addTab(self.tabBulk, "批量转账")

        # 居中显示 & 自适应
        self.adjustSize()

def main():
    app = QApplication(sys.argv)
    w = MainWin(); w.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
