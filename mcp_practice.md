# W10 MCP 实践记录：hsk-tools（HSK 词汇查询服务器）

> 课程：《人工智能在学习环境中的应用与实践》第 10 周 · MCP 与工具生态
> 姓名：`<姓名>`　学号：`<学号>`　日期：2026-11-23
> 交付目录：`week10_MCP/`　主产物：本文件 + `hsk_mcp_server.py` + `hsk_mcp_client.py`

## 0. 一页结论

| 项目 | 结果 |
|------|------|
| 自定义 MCP 服务器 | `hsk_mcp_server.py`，stdio 传输，只读本地 CSV，完全离线 |
| 暴露工具 | `hsk_level(word)`、`list_by_level(level)` |
| 客户端 | `hsk_mcp_client.py`，官方 Python SDK，真实 stdio 握手 |
| `hsk_level("把")` | `把 -> 3 级` |
| `list_by_level("3")` | `把、决定` |
| 验收 | 5 项中 4 项已实测通过；`git push` 待本机执行（见 §2.7） |
| 安全 | 不需要 API key；无 `.env`；服务端零网络、零写入 |

本记录的三样必备内容：**§1 配置记录、§2 调用证据、§3 三者辨析**。

---

## 1. 配置记录

### 1.1 运行环境

| 项 | 值 |
|----|----|
| 操作系统 | Windows 11（NT 10.0.26200） |
| Python | 3.12.4 |
| MCP SDK | `mcp 2.3.0`（主验证）+ `mcp 1.30.0`（兼容验证） |
| 协议版本 | `2025-11-25`（握手协商结果） |
| 传输方式 | `stdio`（标准输入/输出，不占端口） |
| 服务端 | `week10_MCP/hsk_mcp_server.py` |
| 客户端 | `week10_MCP/hsk_mcp_client.py`（官方 SDK） |

### 1.2 依赖安装

```powershell
python -m pip install "mcp[cli]"
python -c "from importlib.metadata import version; print('mcp', version('mcp'))"
```

实测输出：

```text
mcp 2.3.0
```

> **引号必须有**：PowerShell 里方括号是通配符，`pip install mcp[cli]` 可能装错包。
> 如果 `python -c "import mcp"` 失败，说明包装到了另一个解释器，先确认
> `where.exe python` 与 `python -c "import sys; print(sys.executable)"`。

### 1.3 服务端启动记录

| 字段 | 值 |
|------|----|
| 启动命令 | `python hsk_mcp_server.py` |
| 工作目录 | `week10_MCP/`（也可从任意目录用绝对路径启动） |
| 传输 | stdio（默认） |
| 成功标志 | 进程挂起、不退出，最后一行停在“等待客户端连接……” |
| 退出 | `Ctrl+C` |
| 日志 | 只写 `stderr`；`stdout` 留给 JSON-RPC，避免污染协议 |

启动后的 stderr（真实输出，路径已省略为 `<作品集>`）：

```text
[hsk-tools] 数据文件：<作品集>\week10_MCP\data\生词表.csv
[hsk-tools] 已加载 13 条词汇；stdio 服务已启动，等待客户端连接……
```

### 1.4 客户端配置 JSON

桌面客户端使用 `mcpServers` 顶层键。仓库里放模板
`client_config.example.json`（不要把本机绝对路径提交进去）：

```json
{
  "mcpServers": {
    "hsk-tools": {
      "command": "python",
      "args": [
        "D:/ai-portfolio/week10_MCP/hsk_mcp_server.py"
      ]
    }
  }
}
```

本机可用一条命令生成**带绝对路径**的版本，直接粘贴：

```powershell
python hsk_mcp_client.py --print-config
```

字段逐项核对：

| 字段 | 实际值 / 写法 | 说明 |
|------|----------------|------|
| `mcpServers` | 对象 | 顶层键，大小写敏感；写成 `mcpServer` 不生效 |
| `hsk-tools` | 自定义服务名 | 客户端用它显示，可改成别的 |
| `command` | `python` 或绝对路径 | 必须是客户端能执行的解释器；推荐 `--print-config` 的绝对路径 |
| `args` | `[".../hsk_mcp_server.py"]` | **数组**，不是字符串；路径建议绝对路径 |
| `env` | 省略 | 本服务器不需要环境变量；不要把 API key 写进来 |
| `transport` | 不写 | stdio 是默认值；本服务器不监听端口 |

**常见配置错误**（都实际会导致“客户端里看不到工具”）：

1. 顶层写成 `mcpServer` / `mcp_servers`，少一个 `s` 或大小写不对。
2. `args` 写成字符串 `"path/to/server.py"`，而不是数组。
3. 用相对路径：客户端从自己的安装目录解析，找不到文件。
4. `command` 写 `python`，但客户端进程的 `PATH` 里没有 Python；改用绝对路径。
5. 改完配置只关窗口、没完全退出客户端；MCP 配置在启动时加载。
6. 把 `"mcp[cli]"` 的方括号在 PowerShell 里裸写，依赖没装成功。

### 1.5 桌面客户端接入步骤

1. 运行 `python hsk_mcp_client.py --print-config`，复制输出的 JSON。
2. 合并进客户端配置：
   - Claude Desktop（Windows）：`%APPDATA%\Claude\claude_desktop_config.json`
   - Cursor / Windsurf：设置里的 MCP Servers，格式同为 `mcpServers`
   - 其他客户端：以官方文档为准
3. 完全退出客户端并重启。
4. 在工具/MCP 面板应看到 `hsk-tools`，展开有 `hsk_level`、`list_by_level`。
5. 在对话里说“查一下‘把’是 HSK 几级”，客户端应调用 `hsk_level` 并返回
   `把 -> 3 级`。

> **关于截图**：本记录不放置伪造截图。上面所有终端输出都是真实运行结果，
> 可按 §2.6 一键复现；若需要桌面客户端截图，按本节接入后截一张工具面板图
> 存为 `screenshots/tools.png` 即可（本包不预置该图）。

---

## 2. 调用证据

### 2.1 服务端能启动（挂起即成功）

```powershell
PS> python hsk_mcp_server.py
[hsk-tools] 数据文件：<作品集>\week10_MCP\data\生词表.csv
[hsk-tools] 已加载 13 条词汇；stdio 服务已启动，等待客户端连接……
（光标停在这里，不退出 = 成功；Ctrl+C 结束）
```

判定标准：进程没有立刻退出、没有 traceback，日志显示已加载 13 条词汇。
它不是 HTTP 服务，所以**不会**打印 `http://127.0.0.1:xxxx`，也不占端口。

### 2.2 客户端握手 + 列出工具

```powershell
PS> python hsk_mcp_client.py
[1] 握手成功：server=hsk-tools，protocol=2025-11-25
[2] 工具列表（2 个）：hsk_level、list_by_level
    - hsk_level  必填参数=['word']
    - list_by_level  必填参数=['level']
```

这说明：

- `initialize` 握手成功，双方协商到协议版本 `2025-11-25`；
- `tools/list` 返回 2 个工具，名字与预期完全一致；
- 两个工具都有必填参数，说明函数类型注解已正确生成 `inputSchema`。

兼容性附加验证：同一套代码换成 **mcp 1.30.0** 再跑一遍，输出为
`server=hsk-tools 1.30.0`，协议同样协商到 `2025-11-25`，两次调用结果完全一致
（`把 -> 3 级`、`把、决定`）。说明服务端 1.x/2.x 自适应与客户端字段兼容都真实生效。

### 2.3 两次工具调用（本周硬指标）

```text
[3] 调用结果：
    hsk_level({"word": "把"}) -> 把 -> 3 级
    list_by_level({"level": "3"}) -> 把、决定
[通过] MCP 全链路耗时 1.869 秒。
```

对照离场验收：

| 验收要求 | 实测 |
|----------|------|
| `hsk_level("把")` 返回「把 -> 3 级」 | ✅ `把 -> 3 级` |
| `list_by_level` 能按等级查询 | ✅ `list_by_level("3")` → `把、决定` |

`list_by_level` 的其他等级抽查：

| 调用 | 返回 |
|------|------|
| `list_by_level("4")` / `list_by_level("HSK4")` | `把字句、商量、感动、坚持` |
| `list_by_level("5")` | `愚公移山、子子孙孙、无穷无尽` |
| `list_by_level("6")` | `叩石垦壤、寒暑易节、智叟、愚公` |
| `list_by_level("1")` | `1 级暂无词汇` |

### 2.4 结构化证据（`--json` 节选）

```powershell
python hsk_mcp_client.py --json
```

```json
{
  "serverInfo": { "name": "hsk-tools", "version": "" },
  "protocolVersion": "2025-11-25",
  "tools": [
    { "name": "hsk_level", "required": ["word"], "properties": ["word"] },
    { "name": "list_by_level", "required": ["level"], "properties": ["level"] }
  ],
  "calls": [
    {
      "tool": "hsk_level",
      "arguments": { "word": "把" },
      "isError": false,
      "text": "把 -> 3 级"
    },
    {
      "tool": "list_by_level",
      "arguments": { "level": "3" },
      "isError": false,
      "text": "把、决定"
    }
  ],
  "elapsed_seconds": 1.892
}
```

> 在 mcp 2.x 下服务端 `version` 为空，是因为创建 `MCPServer("hsk-tools")` 时未声明版本号；
> 在 mcp 1.30.0 下会自动显示 SDK 版本（`hsk-tools 1.30.0`）。两者都不影响工具发现与调用。

### 2.5 输入校验（安全边界）实测

工具函数先校验、再查表，非法输入不会进入业务逻辑：

| 调用 | 返回 |
|------|------|
| `hsk_level("把")` | `把 -> 3 级` |
| `hsk_level(" 把 ")` | `把 -> 3 级`（自动去首尾空格） |
| `hsk_level("")` | `输入不合法：词语不能为空。` |
| `hsk_level("不存在的词")` | `未找到 不存在的词` |
| `list_by_level("HSK4")` | `把字句、商量、感动、坚持`（兼容 `HSK` / `级` 写法） |
| `list_by_level("99")` | `输入不合法：等级应为 1-9 的整数，收到：99` |
| `list_by_level("abc")` | `输入不合法：等级应为 1-9 的整数，收到：abc` |

### 2.6 一键复现

```powershell
cd week10_MCP
python -m pip install "mcp[cli]"

# 终端 A：启动服务端（挂起即成功）
python hsk_mcp_server.py

# 终端 B：握手 + 列工具 + 调用
python hsk_mcp_client.py

# 可选：机器可读证据 / 生成桌面客户端配置
python hsk_mcp_client.py --json
python hsk_mcp_client.py --print-config

# 提交前自检（不依赖 mcp，也不需要联网）
python preflight_check.py
```

`preflight_check.py` 的实测输出：

```text
W10 交付物自检 —— <作品集>\week10_MCP

[通过] 必需文件齐全（7 个）
[通过] 未发现 .env / .env.* 文件
[通过] 未发现疑似密钥（sk- / Bearer / api_key=…）
[通过] Python 语法检查通过（2 个文件）
[通过] CSV 可解析：13 条词汇，列齐全
[通过] 客户端配置 JSON 可解析，字段齐全
[通过] mcp_practice.md 三节齐全（配置 / 证据 / 辨析）

[全部通过] 可以提交。别忘了最后一步：
  git status        # 确认没有 .env / .pydeps / __pycache__
  git add week10_MCP && git commit -m "W10: MCP hsk-tools" && git push
```

### 2.7 离场验收逐项打钩

| # | 验收项 | 状态 | 证据 |
|---|--------|------|------|
| 1 | mcp 库装好，服务端能启动（挂起等待连接即成功） | ✅ | §1.2 / §2.1 |
| 2 | 客户端能列出 `hsk_level` / `list_by_level` 两个工具 | ✅ | §2.2 |
| 3 | `hsk_level("把")` 返回「把 -> 3 级」，`list_by_level` 能按等级查询 | ✅ | §2.3 |
| 4 | `mcp_practice.md` 三样齐全：配置记录、调用证据、三者辨析 | ✅ | §1 / §2 / §3 |
| 5 | `git status` 无 `.env`；commit + push，远端可见 `week10_MCP/` | ⬜ 待执行 | 本机未装 Git；命令见 README「上传 GitHub」 |

> 第 5 项说明：本机 `git` 不在 PATH（`git --version` 无法识别），所以无法在本记录里
> 伪造 `git status` 输出。`.gitignore` 已覆盖 `.env`、`.pydeps/`、`__pycache__/`，
> 装好 Git 后按 README 执行即可；也可用 GitHub 网页上传。

---

## 3. 三者辨析：Function Calling / MCP / 普通 API 调用

### 3.1 一张表

| 维度 | Function Calling（函数调用） | MCP（Model Context Protocol） | 普通 API 调用（REST / RPC / 本地函数） |
|------|------------------------------|-------------------------------|----------------------------------------|
| 定位 | **模型侧机制** | **工具侧协议** | **应用侧集成** |
| 谁决定调用 | 模型：生成 `tool_calls`，决定调不调、调哪个、参数是什么 | 协议不决定；模型或人决定，客户端执行 | 代码写死：开发者按流程直接调 |
| 工具从哪来 | 开发者把工具名、说明、参数 Schema 随请求交给模型 | MCP 服务器独立提供，客户端通过 `tools/list` 发现 | 后端接口 / 本地函数，读文档后手写 |
| 发现机制 | 无跨应用发现；每次请求带 schema | 标准发现：`tools/list` 返回名称、描述、`inputSchema` | 无；看文档、写死 URL/函数名 |
| 接口/传输 | 各家模型 API 自成一套（OpenAI `tools`、Anthropic `tools`…） | JSON-RPC；stdio / Streamable HTTP 等标准传输 | HTTP、gRPC、进程内函数调用 |
| 复用范围 | 绑定某个应用/某次请求 | 一个服务器可被多个客户端复用 | 每个应用各写一遍 |
| 权限边界 | 由应用执行，应用负责校验 | 服务器自己跑在用户机器上，**不等于可信**；要审代码、限权限 | 由后端/调用方控制 |
| 本项目例子 | W9 `tool_agent.py`：模型输出 JSON 决定调用 | W10 `hsk_mcp_server.py` + `hsk_mcp_client.py` | 若直接 `requests.get(".../hsk?word=把")` |
| 一句话 | 模型“会点菜” | 工具“有标准菜单和传菜口” | 后厨“固定套餐” |

### 3.2 它们不是替代关系，而是三层

```text
用户问题
   │
   ▼
[模型层] Function Calling：模型决定“要调用 hsk_level，参数 word=把”
   │  （模型只输出意图，不自己执行）
   ▼
[协议层] MCP：客户端把意图变成 tools/call，经 JSON-RPC 发给服务器
   │
   ▼
[实现层] 普通 API / 本地函数：服务器读 CSV、查表、返回“把 -> 3 级”
   │
   ▼
结果回填模型 → 模型用自然语言回答用户
```

- **普通 API 是“实现层”**：真正干活的那段代码；MCP 服务器内部也可以调用普通 API。
- **MCP 是“协议层”**：把工具能力标准化，解决“工具怎么被发现、怎么被调用、怎么复用”。
- **Function Calling 是“模型层”**：让模型能表达“我想调用哪个工具、参数是什么”。

本项目的客户端**没有接大模型**，所以只演示了 MCP 的“协议层 + 实现层”：
客户端直接发起 `tools/call`。W9 的 `tool_agent.py` 演示的是“模型层”：
模型输出 `{"tool": "hsk_level", "args": ["把"]}`，再由应用执行。
把两者接起来，就是“模型决定 → MCP 执行”的完整链路。

### 3.3 常见误区（都是会扣分的）

1. **把 MCP 说成“模型压缩 / 量化”**：完全不同的东西。MCP 是 Model Context Protocol；
   量化是把 FP16 权重压成 4 bit，属于模型部署（第 5 讲）。
2. **把 MCP 等同于 Function Calling**：Function Calling 是模型侧能力，MCP 是工具侧协议；
   两者可以叠加，也可以各自单独使用。
3. **认为“服务端 = 可信端”**：MCP 服务器是别人写的代码，跑在你的机器上，能读文件、
   能发网络请求。接第三方 MCP 前先看它要干什么、读什么数据、连哪些域名。
4. **认为 MCP 一定要联网**：stdio 传输就是本地子进程，本项目完全离线，不需要 API key。
5. **工具函数不写类型注解**：MCP 靠类型注解生成 `inputSchema`；不写就会出现
   “客户端能列出工具，但调用时参数对不上”。本项目的 `word: str` / `level: str` 是必需的。
6. **配置键名写错**：`mcpServers` 少 `s`、`args` 不是数组、路径用相对路径，都会导致
   “客户端里没有工具”。

> 如果课堂把“三者”定义为 Function Calling / MCP / Agent，第三列可替换为 Agent：
> Agent 是**编排层**，它会组合 Function Calling 与 MCP 来完成多步任务，但不等于两者。
> 关键不是名词，而是分清“模型侧 / 协议侧 / 应用侧”。

---

## 4. 安全与合规

### 4.1 密钥红线

- 本项目**不需要任何 API key**，因此没有 `.env`，也没有任何密钥可以泄露。
- 不把真实 key 写进代码、不截图含 key 的终端、不把 key 放进作品集。
- `.gitignore` 已包含 `.env`、`.env.*`、`.pydeps/`、`__pycache__/`；
  提交前跑 `preflight_check.py`，再跑 `git status` 人工确认。

### 4.2 服务端的权限边界

`hsk_mcp_server.py` 刻意做成最小权限：

| 能力 | 是否使用 | 说明 |
|------|----------|------|
| 读文件 | 只读 `data/生词表.csv` | 不写文件、不删文件 |
| 网络请求 | ❌ | 没有任何 `requests` / `httpx` / `urllib` |
| 读环境变量 | ❌ | 不读 `os.environ`，不接触 API key |
| 执行系统命令 | ❌ | 没有 `subprocess` / `os.system` |
| 输入校验 | ✅ | 非空、长度 ≤ 20、等级 1–9；非法输入直接返回提示 |

### 4.3 客户端的“最小环境变量”

`hsk_mcp_client.py` 启动服务端时只传：

```text
PATH / PYTHONPATH / PYTHONIOENCODING / PYTHONUTF8 /
SYSTEMROOT / SYSTEMDRIVE / WINDIR / TEMP / TMP / HOME / USERPROFILE / LANG / LC_ALL
```

**不传** `*_API_KEY`、`*_TOKEN` 等秘密。原因：第三方 MCP 服务端能读到你给它的每一个
环境变量；如果直接 `env=os.environ.copy()`，等于把整个 `.env` 递给它。这是本周
“服务端不等于可信端”的一条具体落地。

### 4.4 接第三方 MCP 的检查清单

1. 代码是否只读它声称要读的数据？有没有偷偷扫整个用户目录？
2. 有没有网络请求？连到哪些域名？会不会把本地数据外传？
3. 有没有写文件、执行命令、读环境变量？
4. 工具函数的输入有没有校验？会不会被路径穿越/命令注入？
5. 权限是否最小？能否用只读目录、受限账号、断网环境跑？

本项目就是一份“只读 CSV、零网络、零写入”的对照基线。

---

## 5. 复盘

### 5.1 这周真正搞懂的

1. **MCP 的“挂起”不是卡死**：stdio 服务器启动后就在等客户端写 JSON-RPC，
   没有端口、没有 HTTP 日志，第一次见很容易以为程序坏了。
2. **协议是分层的**：`initialize` → `tools/list` → `tools/call`，每一步都有明确的
   请求/响应；客户端不是“猜”工具名，而是先发现再调用。
3. **类型注解不是装饰**：`word: str` 直接决定 `inputSchema` 里有没有 `word` 字段；
   不写注解，工具在客户端里就是“空参数”。
4. **版本自适应很现实**：mcp 2.x 把 `FastMCP` 改名 `MCPServer`，照旧教程写必炸；
   服务端先试 1.x 再试 2.x，教学环境升级也不会整班跑不起来。
5. **“能跑”与“可信”是两件事**：服务器能返回结果，不代表它不会读你的文件。
   最小权限、输入校验、审代码，一个都不能省。

### 5.2 踩过的坑

| 现象 | 原因 | 处理 |
|------|------|------|
| `ModuleNotFoundError: No module named 'mcp'` | 装到了另一个 Python | `python -m pip install "mcp[cli]"`，并核对 `sys.executable` |
| `ModuleNotFoundError: No module named 'pywintypes'` | 只把依赖装进 `--target` 目录，pywin32 的 DLL 路径没注册 | 正常 `pip install` 到解释器即可；或把 `pywin32_system32` 加进 `PATH` |
| 客户端 `WinError 5 拒绝访问` | 受限沙箱不允许创建匿名管道 | 换普通终端/权限运行；MCP stdio 必须能创建子进程管道 |
| 客户端里没有工具 | `args` 写成字符串 / 路径是相对路径 / 没重启客户端 | 用 `--print-config` 生成绝对路径，完全退出后重启 |
| 中文日志乱码 | 终端代码页与 UTF-8 不一致 | `chcp 65001` 或 `$env:PYTHONUTF8=1`；不影响调用结果 |

### 5.3 如果继续做

- 给 `hsk_level` 增加“按词性/释义模糊查”，但保持只读、可校验。
- 增加 `resources/list`，把《等级标准》节选作为 MCP resource 暴露。
- 写一个“接大模型”的版本：把 `tools/list` 转成 Function Calling 的 `tools` 参数，
  补上“模型层 + 协议层”的完整闭环（对应 W9 + W10）。
- 给服务器加只读目录白名单，演示“即使想读别的文件也会被拒绝”。

---

## 附：本文件对应的可复现文件

| 文件 | 作用 |
|------|------|
| `hsk_mcp_server.py` | MCP 服务器（2 个工具、输入校验、1.x/2.x 自适应） |
| `hsk_mcp_client.py` | 最小客户端（握手、列工具、调用、`--json`、`--print-config`） |
| `client_config.example.json` | 桌面客户端配置模板 |
| `data/生词表.csv` | 13 条 HSK 3–6 级示例词 |
| `preflight_check.py` | 提交前自检（文件/密钥/语法/数据/配置/文档） |
| `README.md` | 安装、运行、接入客户端、上传 GitHub |
