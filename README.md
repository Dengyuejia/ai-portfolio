# ai-portfolio
个人作品集-汉国教f25210105邓悦嘉
@@ -1,0 +1,39 @@
# 第 4 讲作业：Ollama 本地模型 · 笔记与对比实验
《人工智能在学习环境中的应用与实践》第 4 讲「第一次 API 调用」的课后作业仓库。
## 内容
| 文件 | 说明 |
| --- | --- |
| [ollama_notes.md](ollama_notes.md) | 主笔记：安装、选型、课堂 5 问表，以及作业 1/2/3 的完整记录 |
| [experiments/questions.json](experiments/questions.json) | 作业 2 的 8 道学科题、标准答案与评分要点 |
| [experiments/run_bench.py](experiments/run_bench.py) | 复现脚本（只用 Python 标准库，直接调 Ollama HTTP API） |
| [experiments/raw/](experiments/raw) | 两个模型的逐题原始输出与计时（JSON） |
| [experiments/summary.csv](experiments/summary.csv) | 汇总指标（磁盘、常驻内存、速度） |
| [experiments/results.md](experiments/results.md) | 人工评分表与逐题观察 |
| [Modelfile.example](Modelfile.example) | 作业 1 里自定义 Modelfile 的示例 |
## 复现
```powershell
ollama pull qwen2.5:0.5b
ollama pull qwen2.5:3b
python experiments/run_bench.py qwen2.5:0.5b qwen2.5:3b
```
脚本会先预热一次（不计分），然后按 questions.json 的顺序逐题请求，固定
`temperature=0`、`seed=42`、`num_predict=512`、`num_ctx=2048`。
## 实验环境
- Windows 11，Ollama 0.40.6
- CPU 推理（Ollama 检测到 Intel Arc 集显但显存不足，见 `server.log` 中 `dropping integrated GPU`）
- 可用内存 5.1 GiB（Ollama 启动日志 `inference compute ... available="5.1 GiB"`）
- 模型目录：默认 `%USERPROFILE%\.ollama\models`，本机已装好 `qwen2.5:0.5b`、`qwen2.5:3b`、`teacher-helper`
## 提交记录
- `be698e1` 完成第 4 讲作业：Ollama 笔记、0.5B/3B 对比实验与离线部署方案
- 远端仓库：待 push（GitHub / Gitee 均可），push 后把地址补在这里
