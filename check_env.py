# -*- coding: utf-8 -*-
"""环境自检：只读检查，不访问任何网站、不启动浏览器、不修改表格。

用法：python check_env.py
全部 PASS 表示脚本可在本机直接运行；FAIL 项会给出具体修复建议。
"""
import importlib
import json
import os
import re
import sys
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
os.chdir(BASE)

results = []


def add(level, item, detail=""):
    results.append((level, item, detail))


# 1) Python 版本
if sys.version_info >= (3, 9):
    add("PASS", "Python 版本", "%d.%d.%d" % sys.version_info[:3])
else:
    add("FAIL", "Python 版本", "需要 3.9 及以上，当前 %s" % sys.version.split()[0])

# 2) 依赖
for mod, pkg in [("openpyxl", "openpyxl"), ("PIL", "pillow"), ("requests", "requests"),
                 ("bs4", "beautifulsoup4"), ("lxml", "lxml"), ("playwright", "playwright")]:
    try:
        m = importlib.import_module(mod)
        add("PASS", "依赖 %s" % pkg, getattr(m, "__version__", "已安装"))
    except Exception as e:
        add("FAIL", "依赖 %s" % pkg, "缺失：%s → pip install %s" % (type(e).__name__, pkg))

# 3) 配置
try:
    import config
    add("PASS", "config.py 导入", "BASE=%s" % config.BASE)
except Exception as e:
    add("FAIL", "config.py 导入", "%s: %s" % (type(e).__name__, e))
    config = None

local = os.path.join(BASE, "config.local.json")
if os.path.exists(local):
    try:
        with open(local, encoding="utf-8") as f:
            json.load(f)
        add("PASS", "config.local.json", "存在且 JSON 合法（本机配置，不进版本库）")
    except Exception as e:
        add("FAIL", "config.local.json", "JSON 解析失败：%s" % e)
else:
    add("WARN", "config.local.json", "不存在。复制 config.example.json 改名后填写，否则源表路径为空")

if config:
    # 4) 源表
    if config.SRC and os.path.exists(config.SRC):
        add("PASS", "源表 SRC", os.path.basename(config.SRC))
    else:
        add("FAIL", "源表 SRC", "未配置或文件不存在。请在 config.local.json 填 src_xlsx，或设环境变量 SEERFAR_SRC_XLSX")

    # 5) 输出目录可写
    if os.path.isdir(config.OUT_DIR):
        try:
            fd, tmp = tempfile.mkstemp(dir=config.OUT_DIR, prefix=".write_test_")
            os.close(fd)
            os.remove(tmp)
            add("PASS", "输出目录可写", config.OUT_DIR)
        except Exception as e:
            add("FAIL", "输出目录可写", "%s → %s" % (config.OUT_DIR, e))
    else:
        add("WARN", "输出目录", "%s 不存在，脚本会在写入时报错" % config.OUT_DIR)

    # 6) 浏览器
    if os.path.exists(config.CHROME):
        add("PASS", "Chrome/Edge", config.CHROME)
    else:
        add("FAIL", "Chrome/Edge", "未找到浏览器。设 CHROME_PATH 或 config.local.json 的 chrome")

    # 7) 登录态
    if os.path.exists(config.STATE):
        add("PASS", "1688 登录态", "已保存（%d KB），可直接批量" % (os.path.getsize(config.STATE) // 1024))
    else:
        add("WARN", "1688 登录态", "缺失。运行 python login_1688.py 扫码登录一次即可")

    # 8) 缓存
    n_img = len([x for x in os.listdir(config.IMGDIR) if x.lower().endswith((".png", ".jpg", ".webp"))]) \
        if os.path.isdir(config.IMGDIR) else 0
    add("PASS" if n_img else "WARN", "图片缓存", "%d 张，目录 %s" % (n_img, config.IMGDIR))
    if os.path.exists(config.RESULTS):
        try:
            with open(config.RESULTS, encoding="utf-8") as f:
                n = len(json.load(f))
            add("PASS", "抓取结果缓存", "results.json 含 %d 条，可断点续跑" % n)
        except Exception:
            add("WARN", "抓取结果缓存", "results.json 解析失败，将被重建")
    else:
        add("WARN", "抓取结果缓存", "results.json 不存在，首次运行会新建")

# 9) 全部 py 语法编译 + 残留硬编码检查
py_files = sorted(x for x in os.listdir(BASE) if x.endswith(".py"))
bad_syntax, bad_path = [], []
for fn in py_files:
    p = os.path.join(BASE, fn)
    with open(p, encoding="utf-8") as f:
        src = f.read()
    try:
        compile(src, fn, "exec")
    except SyntaxError as e:
        bad_syntax.append("%s:%s %s" % (fn, e.lineno, e.msg))
    for m in re.finditer(r"^[A-Z_]+\s*=\s*r?[\"']([A-Za-z]:[\\/][^\"']+)", src, re.M):
        bad_path.append("%s → %s" % (fn, m.group(1)[:60]))
if bad_syntax:
    add("FAIL", "脚本语法", "；".join(bad_syntax[:5]))
else:
    add("PASS", "脚本语法", "%d 个 .py 全部编译通过" % len(py_files))
if bad_path:
    add("WARN", "残留硬编码路径", "%d 处（%s …）" % (len(bad_path), bad_path[0]))
else:
    add("PASS", "路径配置化", "未发现硬编码绝对路径，可通过 config.local.json 迁移")

# 汇总
icons = {"PASS": "[OK]", "WARN": "[!!]", "FAIL": "[XX]"}
print("=" * 68)
print("脚本环境自检  ·  %s" % BASE)
print("=" * 68)
for lv, item, detail in results:
    print("%-5s %-22s %s" % (icons[lv], item, detail))
n_fail = sum(1 for x in results if x[0] == "FAIL")
n_warn = sum(1 for x in results if x[0] == "WARN")
print("-" * 68)
print("PASS %d / WARN %d / FAIL %d" % (len(results) - n_fail - n_warn, n_warn, n_fail))
if n_fail:
    print("存在 FAIL 项，请先按上面提示修复再运行主脚本。")
else:
    print("环境就绪：先跑 python check_env.py 确认，再跑 LIMIT=30 python batch_run.py 试 30 条。")
sys.exit(1 if n_fail else 0)
