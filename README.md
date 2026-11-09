# 学科智能问答助手 v1.0

把 W6 的双引擎、W7 的知识库问答和 W2 的提示词思路拼成一个能直接用的命令行助手：问教学问题走模型，问标准数字走资料库，云端不可用时自动退回本地。

## 一、功能

- **双引擎**：`prefer="local"` 本地优先、`prefer="api"` 云端优先，任何一边失败都会自动切另一边并打印原因；
- **RAG 开关**：`use_rag=True` 先检索《等级标准》再回答，附出处；`use_rag=False` 直接问模型；
- **命令行 + 交互模式**：一条命令问一个问题，也可以 `-i` 连续追问；
- **零密钥也能跑**：不配云端 key 时自动只走本地，不会一启动就崩。

## 二、怎么装

1. 安装 [Ollama](https://ollama.com/download)，拉两个模型：

   ```powershell
   ollama pull qwen2.5:3b
   ollama pull nomic-embed-text
   ```

2. 安装 Python 依赖（Python 3.10+）：

   ```powershell
   pip install -r requirements.txt
   ```

3. （可选）用云端：复制 `.env.example` 为 `.env`，填入 `DEEPSEEK_API_KEY`。不填也能用，只是 `--prefer api` 会自动回退本地。

## 三、怎么用

```powershell
# 1) 问标准里的数字：走 RAG
python assistant_v1.py "HSK4 累计词汇量是多少"

# 2) 问教学法：知识库里没有，直接问模型
python assistant_v1.py --no-rag "把字句的教学难点有哪些"

# 3) 交互模式
python assistant_v1.py -i

# 4) 云端优先（失败自动回退）
python assistant_v1.py --prefer api "HSK4 累计词汇量是多少"
```

输出示例：

```text
Q: HSK4 累计词汇量是多少
A: HSK4 累计词汇量是 3245。
简要依据：资料[1] 明确指出 HSK4 累计词汇量为 3245。
出处: data.txt·中等四级量化指标；data.txt·二、三等九级与 HSK 的对应关
模式: RAG | 耗时: 15.6s
```

### 官方 RAG 流水线 → 代码映射

| 流水线 | 在本项目里 |
| --- | --- |
| 加载 | `data.txt`（《等级标准》节选） |
| 分块 | `rag_qa.py`，500 字 / 重叠 50 |
| 向量化 | `nomic-embed-text`（Ollama `/api/embed`） |
| 检索 | 余弦 + 领域词加权，top-3 |
| 生成 | `llm.ask()`（W6 统一入口） |

## 四、已知限制

- 知识库只有《等级标准》节选，问“教学法/课堂活动”这类问题会答“资料中未提及”，请加 `--no-rag`；
- 本地 `qwen2.5:3b` 讲语法只到“能听懂”的水平，正式讲义仍要老师改；
- 还没有多轮记忆，每次提问都是独立的；
- 首次运行要建向量索引，约 5 秒，之后复用 `index/`；
- 云端依赖 DeepSeek key，key 失效时会自动回退本地，日志里会打印 401 原因。

## 五、项目结构

```text
week08_助手v1.0/
├── assistant_v1.py     # 入口：参数解析 + 模式切换
├── llm.py              # W6 双引擎
├── rag_qa.py           # W7 检索问答
├── data.txt            # 知识库语料
├── requirements.txt
├── .env.example
├── answer_log.md       # 三个演示问题
└── README.md
```

## 六、发布 v1.0

```powershell
git add .
git commit -m "W8: 学科智能问答助手 v1.0"
git tag -a v1.0 -m "学科智能问答助手 v1.0"
git push origin main --tags
```

然后在 GitHub 仓库的 Releases → Draft a new release，选择 `v1.0` 标签，把 `RELEASE_NOTES.md` 的内容贴进去发布。
