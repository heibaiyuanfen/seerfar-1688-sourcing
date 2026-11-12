# Seerfar OZON 商品表 → 1688 货源识别与成本回填

把 seerfar 导出的 OZON 品类表，用 **1688「以图搜款」** 找同款货源，回填拿货价、国内运费、成本合计与双方图片，输出一份供人工终审的 Excel。

- 主体是**浏览器自动化 + DOM 规则解析**（Playwright 驱动本机 Chrome），不是让大模型猜价格。
- 同款图像相似度由 **1688 平台自己的以图搜款算法**完成；价格、运费、起批量、供应商、offerId 均为页面原值。
- 成本 = 拿货价 + 国内运费；页面未标运费时写「待补」，**不做估算**。
- 不改动源表，另存新 xlsx；原 34 列保留，右侧新增 14 列，OZON 高清图与货源主图嵌入单元格。

## 快速开始（3 步）

```bash
# 1. 装依赖
python -m pip install -r requirements.txt

# 2. 复制配置模板并填写本机路径
cp config.example.json config.local.json
#    编辑 config.local.json：至少填 src_xlsx（源表绝对路径）

# 3. 自检 + 登录 + 试跑
python check_env.py
python login_1688.py          # 弹出 Chrome，扫码登录一次，保存会话
LIMIT=30 python batch_run.py  # 先跑 30 条验质量
LIMIT=200 python batch_run.py # 全表；结果增量写 results.json，中断可续跑

# 全表跑完后做二次质检
python post_audit.py          # 生成「重点复核清单.xlsx」
```

> `check_env.py` 是纯只读检查，不访问网络、不启动浏览器、不修改表格。跑主脚本前先执行它。

## 配置

优先级：**环境变量 > `config.local.json` > 通用默认值**。`config.local.json` 已被 `.gitignore` 排除，**不要提交**。

| config.local.json 键 | 环境变量 | 含义 | 默认值 |
|---|---|---|---|
| `src_xlsx` | `SEERFAR_SRC_XLSX` | seerfar 导出的源 xlsx（**必填**） | 空 |
| `out_dir` | `SEERFAR_OUT_DIR` | 交付 xlsx 输出目录 | 源表所在目录 |
| `chrome` | `CHROME_PATH` | Chrome/Edge 可执行文件 | 自动探测常见安装位置 |
| `state` | `STATE_1688` | 1688 登录态 JSON | 脚本目录 |
| `profile` | `CHROME_PROFILE` | 登录用 Chrome 配置目录 | 脚本目录 |
| `results` | `SEERFAR_RESULTS` | 增量抓取结果 | 脚本目录 `results.json` |
| `imgdir` | `SEERFAR_IMGDIR` | 图片缓存目录 | 脚本目录 `sample_images/` |
| — | `LIMIT` | 本批处理条数 | `30` |

把 `state` / `results` / `imgdir` 指向已有缓存，可以直接断点续跑，不必重新登录或重下图片。

## 脚本清单

**核心链路（日常只用这几个）**

| 脚本 | 作用 |
|---|---|
| `config.py` | 集中配置，所有脚本从这里取路径 |
| `check_env.py` | 只读环境自检 |
| `login_1688.py` | 有头 Chrome 等扫码登录，保存 `storage_state` |
| `batch_run.py` | **主脚本**：以图搜款 → 抓候选 → 生成全表 xlsx |
| `post_audit.py` | 全表质检，产出分级「重点复核清单」 |
| `export_context.py` | 可选：导出对话上下文包（需另配 `export_*` 项） |

**一次性探测脚本（保留作技术记录，日常无需运行）**

`inspect_xlsx.py`、`test_network.py`、`probe_1688.py`、`browser_probe.py`、`build_sample.py`、`build_full_sample.py`、`restore_sample.py`、`probe_logged.py`、`image_search.py`、`probe_cards.py`、`probe_captcha.py`、`pass_captcha.py`、`probe_air_direct.py`、`test_air_reupload.py`。

其中 `probe_air_direct.py` / `test_air_reupload.py` 记录了**绕过滑块验证的关键发现**：`s.1688.com` 搜索页会触发风控，但 `air.1688.com` 的图搜结果页不受影响，且可在结果页内换图上传刷新结果——批量链路即建立在此之上。

## 已知限制

- **DOM 脆弱**：卡片类名 `searchOfferWrapper--St2OXxYo`、主图 `mainImg--KwnHnbbk` 带构建 hash，1688 改版后需重调 `batch_run.py` 里的 `PARSE_CARDS` 与选择器。
- **同款判定有假阳性**：置信度是「图搜 Top1 + 标题关键词命中」的启发式规则。实测 200 条里 58 行 Top1 明显跨品类、其中 18 行被误判为「高」。**置信度不能单独作为终审依据**，务必配合 `post_audit.py` 的清单人工复核。
- **1688 标价**常是单件/引流规格价（如 ¥0.17），不等于整套拿货价，需核对起批规格。
- 风控策略可能变化；脚本已内置失败重置页面与 2.5 秒间隔，仍建议分批慢跑。

## 安全与合规

- `1688_storage_state.json` 含登录 Cookie，属于**凭证**，已由 `.gitignore` 排除，**不要提交、不要外传**。
- 源表、交付表、`results.json`、图片缓存均为业务数据，同样已排除。
- 本仓库包含针对 1688 页面结构的抓取与风控规避逻辑，且涉及 OZON/1688 平台数据。**建议设为私有仓库**；公开前请确认平台条款与公司数据外发合规要求。

## 输出列（原 34 列之后新增 14 列）

`OZON高清主图` · `中文检索关键词` · `1688搜索直达` · `货源链接` · `货源商品标题` · `拿货价(¥)` · `起批量` · `国内运费(¥)` · `成本合计(¥)` · `货源主图` · `匹配依据` · `置信度` · `审核状态` · `备注`

每行还附 3 个备选候选（含 offerId 与价格）、供应商、引流价提示；审核状态统一「待确认」。
