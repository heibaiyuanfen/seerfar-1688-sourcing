# -*- coding: utf-8 -*-
"""导出本次会话上下文，供外部模型复现。自动剔除凭证与内部推理内容。"""
import json
import os
import re
import shutil
import zipfile
import datetime

from config import *
OUT = EXPORT_OUT
JSONL = EXPORT_JSONL
ZIP = EXPORT_ZIP

# BASE 由 config.py 提供
# OUT 由 config.py 提供
SCRIPTS = os.path.join(OUT, "scripts")
# JSONL 由 config.py 提供
# ZIP 由 config.py 提供

ROLES = {"user": "用户", "assistant": "助手"}

SCRIPT_DESC = {
    "inspect_xlsx.py": "读取源表结构、表头、行数与链接列样例",
    "test_network.py": "实测 OZON 图片 CDN / 商品页与 1688 连通性",
    "probe_1688.py": "探测 1688 搜索页静态 HTML 能否解析出商品（结论：JS 空壳）",
    "browser_probe.py": "用系统 Chrome 渲染 1688 搜索页（发现直接跳淘宝登录页）",
    "build_sample.py": "生成 5 条格式样本：OZON 高清图 + 检索词 + 搜索直达 + 列骨架",
    "login_1688.py": "开有头 Chrome 等用户扫码登录 1688，保存 storage_state 会话",
    "probe_logged.py": "登录后校准关键词、定位「以图搜款」上传入口",
    "image_search.py": "上传 OZON 图片并点击「搜索图片」，验证同款结果",
    "probe_cards.py": "解析图搜结果页商品卡片的 DOM 结构与字段位置",
    "build_full_sample.py": "用真实图搜结果回填 5 条完整货源样本",
    "probe_captcha.py": "探测并尝试自动通过阿里滑块验证（失败）",
    "restore_sample.py": "重建被误覆盖的 3 条真实货源数据样本",
    "pass_captcha.py": "开有头窗口等待人工过滑块（5 分钟未通过）",
    "probe_air_direct.py": "关键突破：直连 air.1688.com 图搜结果页不受风控",
    "test_air_reupload.py": "验证在结果页内换图可刷新 imageId 与同款结果",
    "batch_run.py": "最终批量脚本：增量抓货源 + 生成全表 200 行交付 xlsx",
    "post_audit.py": "全表跑完后的本地二次质检，产出「重点复核清单」（不重访 1688）",
}

REDACT = [
    (re.compile(r"(?:_m_h5_tk|cookie2|sgcookie|XSRF-TOKEN|[Cc]ookie|[Aa]uthorization|[Pp]assword|[Ss]ecret|[Tt]oken)\s*[:=]\s*[\"']?[^\s\"',};]{8,}", re.I), "***REDACTED***"),
    (re.compile(r"<system-reminder[\s\S]*?</system-reminder>", re.I), ""),
]
SYS_BLOCK = re.compile(r"<system-reminder[\s\S]*?</system-reminder>", re.I)


def clean(s, keep_sys=False):
    if not isinstance(s, str):
        s = str(s)
    if not keep_sys:
        s = SYS_BLOCK.sub("", s)
    for pat, rep in REDACT:
        s = pat.sub(rep, s)
    return s.strip()


def clip(s, n):
    s = clean(s)
    if len(s) <= n:
        return s
    return s[:n] + "\n…（此处截断，完整内容见原始记录）"


def extract_content(msg):
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        buf = []
        for it in c:
            if not isinstance(it, dict):
                continue
            t = it.get("type", "")
            if t in ("input_text", "output_text", "text", "reasoning_text"):
                buf.append(it.get("text", ""))
            elif t == "tool_result":
                buf.append(str(it.get("content", "")))
        return "\n".join(x for x in buf if x)
    return ""


def fmt_time(d):
    ts = d.get("timestamp")
    if not ts:
        return ""
    try:
        return datetime.datetime.fromtimestamp(ts / 1000).strftime("%m-%d %H:%M:%S")
    except Exception:
        return ""


def main():
    os.makedirs(SCRIPTS, exist_ok=True)
    records = []
    md = [
        "# 本次会话对话记录（完整可读版）",
        "",
        "> 导出时间：2026-11-12 15:57 (GMT+8)",
        "> 已剔除内部推理、系统提醒、文件快照，以及疑似凭证串。",
        "> 工具结果过长时截断；完整结构化记录见 `02_对话原始记录.jsonl`。",
        "",
        "---",
        "",
    ]
    brief = [
        "# 本次会话对话记录（精简版，适合直接粘贴给模型）",
        "",
        "> 只保留用户与助手的发言，工具调用仅列名称，不含输出。",
        "> 需要技术细节请读 `00_README_复现上下文.md` 与 `scripts/`。",
        "",
        "---",
        "",
    ]

    with open(JSONL, encoding="utf-8") as f:
        lines = [json.loads(x) for x in f if x.strip()]

    for d in lines:
        t = d.get("type")
        if t == "message":
            role = d.get("role", "")
            body = clean(extract_content(d))
            if not body:
                continue
            md.append("### [%s] %s" % (fmt_time(d), ROLES.get(role, role)))
            md.append("")
            md.append(body)
            md.append("")
            brief.append("**[%s] %s**：%s" % (fmt_time(d), ROLES.get(role, role), body.replace("\n", " ")[:1400]))
            brief.append("")
            records.append({"type": "message", "timestamp": d.get("timestamp"),
                            "role": role, "content": body})
        elif t == "function_call":
            name = d.get("name", "?")
            args = d.get("arguments", "")
            if isinstance(args, (dict, list)):
                args = json.dumps(args, ensure_ascii=False)
            md.append("- **工具调用 `%s`**（%s）" % (name, fmt_time(d)))
            a = clip(args, 700)
            if a:
                md.append("```")
                md.append(a)
                md.append("```")
            md.append("")
            records.append({"type": "function_call", "timestamp": d.get("timestamp"),
                            "name": name, "arguments": clip(args, 4000)})
        elif t == "function_call_result":
            name = d.get("name", "?")
            out = d.get("output", "")
            if isinstance(out, dict):
                out = out.get("text") or json.dumps(out, ensure_ascii=False)
            if not isinstance(out, str):
                out = json.dumps(out, ensure_ascii=False)
            md.append("- **工具结果 `%s`**（%s, %s）" % (name, fmt_time(d), d.get("status", "")))
            o = clip(out, 1200)
            if o:
                md.append("```text")
                md.append(o)
                md.append("```")
            md.append("")
            records.append({"type": "function_call_result", "timestamp": d.get("timestamp"),
                            "name": name, "status": d.get("status"), "output": clip(out, 6000)})

    with open(os.path.join(OUT, "01_对话记录.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    with open(os.path.join(OUT, "01_对话记录_精简.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(brief) + "\n")

    with open(os.path.join(OUT, "02_对话原始记录.jsonl"), "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    idx = ["# 脚本索引", "",
           "> 按实际编写/运行顺序排列。`batch_run.py` 是最终交付脚本。", "",
           "| 脚本 | 作用 | 大小 |", "|---|---|---|"]
    copied = []
    for name in sorted(SCRIPT_DESC):
        src = os.path.join(BASE, name)
        if not os.path.exists(src):
            continue
        shutil.copy2(src, os.path.join(SCRIPTS, name))
        copied.append(name)
        idx.append("| `%s` | %s | %s KB |" % (name, SCRIPT_DESC[name],
                                            round(os.path.getsize(src) / 1024, 1)))
    idx += ["", "未打包：`1688_storage_state.json`（登录凭证）、`results.json` 与图片缓存（业务数据）。", ""]
    with open(os.path.join(OUT, "03_脚本索引.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(idx) + "\n")

    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(OUT):
            for fn in files:
                full = os.path.join(root, fn)
                z.write(full, os.path.relpath(full, os.path.dirname(OUT)))

    print("OUT:", OUT)
    print("ZIP:", ZIP, round(os.path.getsize(ZIP) / 1024, 1), "KB")
    print("scripts copied:", len(copied))
    print("records:", len(records))
    print("dialogue md:", round(os.path.getsize(os.path.join(OUT, "01_对话记录.md")) / 1024, 1), "KB")
    print("dialogue brief:", round(os.path.getsize(os.path.join(OUT, "01_对话记录_精简.md")) / 1024, 1), "KB")
    print("raw jsonl:", round(os.path.getsize(os.path.join(OUT, "02_对话原始记录.jsonl")) / 1024, 1), "KB")


if __name__ == "__main__":
    main()
