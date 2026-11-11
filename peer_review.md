# 第 8 周互评记录

- 评阅对象：GitHub 账号 `huanlingphantom`（仓库内未提供姓名）
- 对象仓库：https://github.com/huanlingphantom/ai-portfolio
- 对象版本：`main` @ `f08eaae`（2026-11-09 06:05 UTC）
- 评审时间：2026-11-11
- 评审环境：Windows 11 / Python 3.12 / Ollama 0.40.11（已装 `qwen2.5:0.5b`、`nomic-embed-text`）
- 纪律：只描述现象，不打分、不评价人

## 一、我照着做的步骤与看到的报错原文

1. 按 README「怎么装」第 1 步，在 `week8` 目录执行：

   ```text
   pip install -r requirements.txt
   ```

   本机 pip 未完成安装，报错原文（节选）：

   ```text
   ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied:
   'C:\Users\31397\AppData\Local\Temp\...\pip-unpack-...\requests-...whl'
   ```

2. 依赖未装成，仍按 README「怎么用」直接执行：

   ```text
   cd week8
   python assistant_v1.py
   ```

   报错原文：

   ```text
   File "...\week6\llm.py", line 33, in <module>
       import requests
   ModuleNotFoundError: No module named 'requests'
   ```

3. 因此没有进入「三问三答」环节，未观察到运行结果。

## 二、四个维度的现象

### 1. 能不能跑

- **现象**：在评审机上未能跑起来，卡在依赖安装这一步（见上）。
- 静态核对（只读代码）：
  - `week8/assistant_v1.py` 存在，`answer(question, use_rag=True, prefer="local")` 三个参数齐全；
  - 通过根目录 `weekpath.py` 注册 `week6`、`week7` 后 `from llm import LLM`、`from rag_qa import retrieve, build_prompt`；
  - `retrieve(question)` 返回带编号的字符串，`build_prompt(question, ctx)` 的签名与 `week7/rag_qa.py` 一致，未发现参数错配；
  - 入口在 `__main__` 里写死三个问题，任一问异常只打印「运行失败：原因」。
- 仓库内 `week8/answer_log.md`、`w8_answer_raw.json` 记录了三问 × 四组合的回答与耗时，属于对方机器上的运行证据，本次未能在评审机复现。

### 2. README 能复现吗

- README 四段齐全：功能 / 怎么装 / 怎么用 / 已知问题。
- 「怎么装」写到具体命令：`pip install -r requirements.txt`、`ollama pull qwen2.5:0.5b`、`ollama pull nomic-embed-text`、Windows 下的 `copy .env.example .env`，并提示 `.env` 不要提交。
- 「怎么用」明确要求 `cd week8` 再运行，并提醒不要在仓库根目录直接跑（跨周 import 依赖根目录 `weekpath.py`）。
- **卡点**：第 1 步装依赖在评审机失败（错误原文见上），后面步骤无法继续。

### 3. Release 发了吗

- 仓库有 `v1.0` 标签，`/releases` 有对应页面：`学科智能问答助手 v1.0`（2026-11-09 05:23 UTC 发布）。
- Release 说明包含四块：功能（RAG、`use_rag` 开关、`prefer` 双引擎、三问三答）、安装（`pip install -r week8/requirements.txt`、两个 `ollama pull`、复制 `.env`）、用法（`cd week8 && python assistant_v1.py`）、已知问题（3 条）。

### 4. 有没有已知限制

- README「已知问题」列了 6 条，均为具体现象：
  1. 未启动 Ollama 时本地模式报 `ConnectionError`；
  2. 缺 `nomic-embed-text` 时建库失败；
  3. 小模型不写「出处：[n]」（云端 5/5、本地 0/3）；
  4. 知识库只覆盖 `data/等级标准节选.txt`，语料外问题检索帮助有限；
  5. `qwen2.5:0.5b` 读不懂四列数字表，建议换 1.5b 或云端；
  6. 首次运行建库 10–20 秒。
- Release 页摘了其中 3 条，与 README 一致。

## 三、其他观察（只描述现象）

- 默认本地模型是 `qwen2.5:0.5b`，README 已知问题里也承认它读表不稳，并给了 `LOCAL_MODEL=qwen2.5:1.5b` 的改法。
- `assistant_v1.py` 没有命令行参数，三个问题写死在 `__main__`，`use_rag`/`prefer` 需要 `from assistant_v1 import answer` 在 Python 里调用。
- `week8/` 下另有 `RAG流水线映射表.md`、`answer_log.md`、`w8_run.py`、`w8_answer_raw.json`、`reflect.md` 等过程文件。

## 四、说明

本记录只描述 2026-11-11 在评审机上的操作与现象。依赖安装失败是评审环境的网络/权限限制所致，不代表对方仓库在正常环境下不能运行；「能不能跑」这一项本次未能独立验证。
