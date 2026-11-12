# -*- coding: utf-8 -*-
"""集中配置。

优先级：环境变量 > config.local.json > 内置通用默认值。
config.local.json 保存本机实际路径，已被 .gitignore 排除，**不要提交**。

所有脚本通过 `from config import *` 读取这些常量，便于整体迁移到任意目录。
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
LOCAL_CFG = os.path.join(BASE, "config.local.json")

_cfg = {}
if os.path.exists(LOCAL_CFG):
    with open(LOCAL_CFG, "r", encoding="utf-8") as _f:
        _cfg = json.load(_f)


def get(key, env, default=""):
    """环境变量优先，其次本机配置文件，最后通用默认值。"""
    return os.environ.get(env) or _cfg.get(key) or default


def _find_chrome():
    candidates = [
        get("chrome", "CHROME_PATH", ""),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return candidates[1]


# ---- 输入：seerfar 导出的 OZON 商品表（必填，在 config.local.json 或环境变量中配置）----
SRC = get("src_xlsx", "SEERFAR_SRC_XLSX", "")

# ---- 输出目录：默认与源表同目录；源表未配置时落到脚本目录 ----
OUT_DIR = get("out_dir", "SEERFAR_OUT_DIR", "") or (os.path.dirname(SRC) if SRC else BASE)


def _out(name):
    return os.path.join(OUT_DIR, name)


DST_FULL = get("dst_full", "SEERFAR_DST_FULL", _out("Seerfar-电子清洁刷_全表_已补全.xlsx"))
DST_SAMPLE_FULL = get("dst_sample_full", "SEERFAR_DST_SAMPLE_FULL",
                      _out("Seerfar-电子清洁刷_样本5条_完整版.xlsx"))
DST_SAMPLE_SKELETON = get("dst_sample_skeleton", "SEERFAR_DST_SAMPLE_SKELETON",
                          _out("Seerfar-电子清洁刷_样本5条_待审.xlsx"))
AUDIT_SRC = get("audit_src", "SEERFAR_AUDIT_SRC", DST_FULL)
AUDIT_DST = get("audit_dst", "SEERFAR_AUDIT_DST", _out("Seerfar-电子清洁刷_重点复核清单.xlsx"))

# ---- 运行期数据（默认放在脚本目录，可用配置指向已有缓存以断点续跑）----
CHROME = _find_chrome()
STATE = get("state", "STATE_1688", os.path.join(BASE, "1688_storage_state.json"))
PROFILE = get("profile", "CHROME_PROFILE", os.path.join(BASE, "chrome_profile_1688"))
RESULTS = get("results", "SEERFAR_RESULTS", os.path.join(BASE, "results.json"))
IMGDIR = get("imgdir", "SEERFAR_IMGDIR", os.path.join(BASE, "sample_images"))
OUT = IMGDIR
FULL_IMG = os.path.join(IMGDIR, "ozon_full_1898568498.png")
LOGIN_HINT = os.path.join(BASE, "1688_login_window.png")

# ---- 批量条数 ----
LIMIT = int(os.environ.get("LIMIT", "30"))

# ---- 仅 export_context.py 使用（可选工具）----
EXPORT_OUT = get("export_out", "EXPORT_OUT", "")
EXPORT_JSONL = get("export_jsonl", "EXPORT_JSONL", "")
EXPORT_ZIP = get("export_zip", "EXPORT_ZIP", "")

__all__ = [
    "BASE", "SRC", "OUT_DIR", "DST_FULL", "DST_SAMPLE_FULL", "DST_SAMPLE_SKELETON",
    "AUDIT_SRC", "AUDIT_DST", "CHROME", "STATE", "PROFILE", "RESULTS", "IMGDIR",
    "OUT", "FULL_IMG", "LOGIN_HINT", "LIMIT", "EXPORT_OUT", "EXPORT_JSONL", "EXPORT_ZIP",
]
