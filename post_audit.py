# -*- coding: utf-8 -*-
"""全表跑完后的本地二次质检：不改主表，单独产出「重点复核清单」。
仅基于已抓到的页面数据做规则筛查，不重新访问 1688，不编造任何数值。
"""
import os
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from config import *
SRC = AUDIT_SRC
DST = AUDIT_DST

# SRC 由 config.py 提供
# DST 由 config.py 提供

# 明确属于其它品类的词：命中即说明 1688 图搜把不相干商品当成了主体
OFF_CATEGORY = [
    "牙刷", "油画", "画笔", "丙烯", "颜料", "化妆刷", "散粉刷", "腮红", "眼线",
    "花洒", "淋浴", "莲蓬", "喷头", "浴室", "瓷砖", "灶台", "燃气灶", "锅",
    "奶瓶", "杯盖", "保温杯", "吸管刷", "咖啡机", "榨汁机", "摇摇杯", "水杯",
    "硅胶杯套", "服装", "裤夹", "裤架", "磨牙", "婴儿", "儿童丙烯",
    "榴莲球", "穴位", "瑜伽", "3d打印", "热端", "Elegoo",
    "电动牙刷", "扫地机", "无线电动刷", "原装博世", "电动清洁刷", "旋转无线",
    "顺丰次日达", "无线蓝牙耳机", "蓝牙耳机air", "华强北",
    "无尘净化棉签", "棉签海绵", "油画笔", "油漆刷", "美术", "绘画",
    "牙缝刷", "牙间刷", "助听器", "按摩", "瑜伽",
]

HEADERS = ["优先级", "主表行号", "OZON SKU", "OZON 标题(俄文)", "1688 图搜 Top1 标题",
           "拿货价(¥)", "国内运费(¥)", "成本合计(¥)", "原置信度", "复核原因", "建议动作"]
WIDTHS = [9, 11, 14, 40, 46, 12, 13, 13, 11, 34, 30]


def main():
    ws = openpyxl.load_workbook(SRC)["Data"]
    rows = []
    for r in range(2, ws.max_row + 1):
        sku = str(ws.cell(r, 6).value or "").replace(".0", "")
        ru = str(ws.cell(r, 4).value or "")
        top = str(ws.cell(r, 39).value or "")
        price = ws.cell(r, 40).value
        freight = ws.cell(r, 42).value
        cost = ws.cell(r, 43).value
        level = str(ws.cell(r, 46).value or "")

        reasons = []
        hits = [k for k in OFF_CATEGORY if k in top]
        if hits:
            reasons.append("跨品类词命中：" + "、".join(hits[:4]))
        if level in ("低", "中", "未匹配"):
            reasons.append("置信度为%s" % level)
        if freight == "待补" or (isinstance(cost, str) and cost == "待补"):
            reasons.append("页面未标运费，成本待补")

        if not reasons:
            continue

        if hits and level == "高":
            pri, action = "P1", "重点复核：置信度被高估，建议直接剔除或换候选"
        elif hits:
            pri, action = "P2", "疑似非同款，建议从备选候选里另选"
        elif level == "未匹配":
            pri, action = "P2", "本条抓取失败，需补跑或人工找货"
        elif level == "低":
            pri, action = "P3", "低置信，核对主图与规格后决定"
        elif cost == "待补" or freight == "待补":
            pri, action = "P4", "补齐国内运费后成本公式会自动生效"
        else:
            pri, action = "P3", "中置信，建议目视确认"

        rows.append([pri, r, sku, ru[:120], top[:120], price, freight,
                     cost, level, "；".join(reasons), action])

    order = {"P1": 0, "P2": 1, "P3": 2, "P4": 3}
    rows.sort(key=lambda x: (order[x[0]], x[1]))

    wb = openpyxl.Workbook()
    out = wb.active
    out.title = "重点复核清单"
    out["A1"] = "重点复核清单 · 依据已抓取的页面数据做本地规则筛查，不含任何推测数值"
    out["A1"].font = Font(bold=True, size=12, color="C00000")
    out.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(HEADERS))
    out.row_dimensions[1].height = 24

    fill = PatternFill("solid", fgColor="4472C4")
    for j, h in enumerate(HEADERS, 1):
        c = out.cell(row=2, column=j, value=h)
        c.font = Font(bold=True, color="FFFFFF", size=10)
        c.fill = fill
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        out.column_dimensions[get_column_letter(j)].width = WIDTHS[j - 1]
    out.row_dimensions[2].height = 28

    colors = {"P1": "FFC7CE", "P2": "FFE699", "P3": "FFF2CC", "P4": "E2EFDA"}
    for i, row in enumerate(rows, 3):
        for j, v in enumerate(row, 1):
            c = out.cell(row=i, column=j, value=v)
            c.alignment = Alignment(wrap_text=True, vertical="center")
        out.cell(i, 1).fill = PatternFill("solid", fgColor=colors[row[0]])
        out.cell(i, 1).font = Font(bold=True)
        if row[0] == "P1":
            out.cell(i, 9).font = Font(bold=True, color="C00000")
        out.row_dimensions[i].height = 46

    out.freeze_panes = "A3"
    out.auto_filter.ref = "A2:%s%d" % (get_column_letter(len(HEADERS)), len(rows) + 2)
    wb.save(DST)

    print("SAVED", DST, round(os.path.getsize(DST) / 1024, 1), "KB")
    print("review rows", len(rows))
    from collections import Counter
    print("priority", dict(Counter(x[0] for x in rows)))
    print("P1 rows", [(x[1], x[2], x[4][:26]) for x in rows if x[0] == "P1"][:20])


if __name__ == "__main__":
    main()
