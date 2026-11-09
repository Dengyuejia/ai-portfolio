# 第 8 周互评记录：照「照着装」验收

- 被评仓库：https://github.com/huahuochai/ai-portfolio
- 评审对象：学科智能问答助手 v1.0（第 8 周阶段项目一）
- 评审时间：2026-11-09
- 仓库状态：`main` 分支，最新提交 `ae43ca0`（2026-11-08 07:18 UTC），共 56 个文件
- 评审方式：只看仓库里能拿到的东西，按 README 的「怎么装 / 怎么用」照做；只记录现象，不打分、不评价人

## 一、逐项现象

### 1. 能不能跑

- 检查方法：拉取仓库文件树，查找 `week08_助手v1.0/assistant_v1.py`。
- 看到的现象：
  - 仓库目录只有 `week01_环境` 到 `week07_RAG`，**没有 `week08_助手v1.0` 目录**；
  - 全仓库 56 个文件里没有 `assistant_v1.py`；
  - 因此无法执行 `python assistant_v1.py`，三个学科问题也没有可运行的入口。
- 证据：GitHub 文件树（`/git/trees/main?recursive=1`）与根目录列表。

### 2. README 能复现吗

- 检查方法：找根目录 `README.md`，看是否有「怎么装 / 怎么用」。
- 看到的现象：
  - 根目录**没有 `README.md`**；
  - 唯一的 README 在 `week01_环境/README.md`，内容是第 1 周的环境说明，不是本项目的安装/使用文档；
  - 没有 `requirements.txt`，也没有说明依赖哪几个包、要不要先 `ollama pull`。
- 结论：无法照着装。

### 3. Release 发了吗

- 检查方法：查仓库的 tags 与 releases。
- 看到的现象：
  - `/tags` 返回空数组；
  - `/releases` 返回空数组；
  - 仓库只有 `main` 一个分支，没有 `v1.0` 标签，也没有 Release 页面。
- 结论：未发布。

### 4. 有没有已知限制

- 检查方法：在 README 中找「已知问题 / 已知限制」段落。
- 看到的现象：
  - 没有根 README，也就没有已知限制的说明；
  - `week07_RAG/week08_预习.md` 里列了三条「需要补齐的功能」：交互界面、多轮记忆、错误处理——这是预习计划，不是 README 里的已知限制。

## 二、仓库里已有的内容（仅记录）

| 周次 | 目录 | 能看到的东西 |
| --- | --- | --- |
| W1 | `week01_环境` | README、ai 任务单、hello.py |
| W2 | `week02_提示词` | prompt-library 下 8 个模板、迭代实录 |
| W3 | `week03_Python` | vocab_tool.py、生词表、练习文件 |
| W4 | `week04_API` | week4_api_bot.py、chat_log、密钥自查表、三次课后作业 |
| W5 | `week05_本地部署` | ollama_notes.md、体验截图、课后作业 |
| W6 | `week06_双引擎` | llm.py、测试反思、预习 |
| W7 | `week07_RAG` | rag_qa.py、hallucination_log、week08 预习 |

## 三、本次验收结论（只描述现象）

按「照着装」这一条标准，本次验收**未能开始**：目标文件 `assistant_v1.py` 不在仓库里，没有安装说明，也没有 Release，因此「装—跑—三问」三步都无法进行。仓库里能看到的是 W1–W7 的内容，以及 `week07_RAG/week08_预习.md` 里的项目规划。

## 四、复评方式

等对方把第 8 周内容 push 上来后，按同样四项再看一遍即可：

1. `python assistant_v1.py` 是否无报错，三个问题是否都有回答；
2. 照着根目录 README 的「怎么装 / 怎么用」能否跑通；
3. 是否有 `v1.0` 标签和 Release 页面；
4. README 是否写了「已知限制」。

本记录只描述 2026-11-09 这次查看时的状态，不代表对方最终提交结果。
