# W9 手写最小工具调用循环（不用框架）
#
# 三个工具：get_time / calc / hsk_level
# 循环：模型输出 JSON → 解析 → 执行工具 → 把结果回喂 → 直到模型给出最终回答
# 安全：calc 用白名单 AST，不用 eval；越权表达式被拒绝并记录
#
# 运行：
#   python tool_agent.py                 # 跑 3 条演示轨迹，写 tool_trace.md
#   python tool_agent.py "现在几点"       # 单问
#
# 引擎：有 DEEPSEEK_API_KEY 用云端，没有就用本机 Ollama 的 OpenAI 兼容接口

import ast
import csv
import datetime
import json
import operator
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

try:  # 仓库里通常有 weekpath；单独拷出来也能跑
    import weekpath  # noqa: E402

    weekpath.load_env()
    VOCAB = weekpath.data_path("生词表.csv")
except Exception:  # noqa: BLE001
    VOCAB = HERE / "生词表.csv"
    env = HERE / ".env"
    if env.is_file():
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

import openai  # noqa: E402

_client = None
_model = None
REJECTED = []   # 被拒绝的计算表达式，留作审计记录


def get_client():
    """有云端 key 走 DeepSeek，没有就走本机 Ollama 的 OpenAI 兼容接口。"""
    global _client, _model
    if _client is None:
        key = os.getenv("DEEPSEEK_API_KEY")
        if key:
            _client = openai.OpenAI(base_url="https://api.deepseek.com/v1", api_key=key)
            _model = "deepseek-chat"
        else:
            base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            _client = openai.OpenAI(base_url=base, api_key="ollama")
            _model = os.getenv("AGENT_MODEL", "qwen2.5:3b")
    return _client, _model


def get_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ---- 安全计算：白名单 AST，绝不使用裸 eval ----
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("只允许数字与 + - * / ** % 运算")


def calc(expr):
    """只做算术。用 eval 会执行任意 Python 代码，是典型安全反模式。"""
    try:
        value = _eval_node(ast.parse(str(expr), mode="eval"))
        return str(value)
    except ZeroDivisionError:
        return "错误：除数为 0"
    except Exception as e:  # noqa: BLE001
        REJECTED.append({"expr": str(expr), "reason": str(e),
                         "at": datetime.datetime.now().strftime("%H:%M:%S")})
        return "拒绝计算：%s" % e


def hsk_level(word):
    path = VOCAB
    if not Path(path).is_file():
        return "未找到生词表：%s" % path
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["词汇"].strip() == str(word).strip():
                return "%s 是 %s 级" % (word, row["HSK等级"])
    return "未找到 %s" % word


TOOLS = {"get_time": get_time, "calc": calc, "hsk_level": hsk_level}

SYS = (
    "你是国际中文助教。你可以使用三个工具：\n"
    '- get_time：参数 []，返回当前时间\n'
    '- calc：参数 ["算术表达式"]，只支持数字和 + - * / ** %\n'
    '- hsk_level：参数 ["词语"]，查 HSK 等级\n'
    "需要工具时只输出一行 JSON，不要解释，例如："
    '{"tool": "hsk_level", "args": ["把"]}\n'
    "一次只调用一个工具；拿到工具结果后，如果需要再用工具，继续输出 JSON；"
    "如果不需要工具或已经能回答，直接用中文回答。"
)


def parse_calls(txt):
    """模型一次可能只给一个 JSON，也可能一口气给多个；都收下来。"""
    s = (txt or "").strip().replace("```json", "").replace("```", "").strip()
    try:
        obj = json.loads(s)
        return [obj] if isinstance(obj, dict) and obj.get("tool") in TOOLS else []
    except Exception:  # noqa: BLE001
        pass
    calls, dec, i = [], json.JSONDecoder(), 0
    while i < len(s):
        j = s.find("{", i)
        if j < 0:
            break
        try:
            obj, end = dec.raw_decode(s[j:])
            if isinstance(obj, dict) and obj.get("tool") in TOOLS:
                calls.append(obj)
            i = j + end
        except Exception:  # noqa: BLE001
            i = j + 1
    return calls


def run(user_msg, max_calls=4):
    """返回 (最终回答, 轨迹步骤列表)。每步记录：模型输出 / 工具 / 参数 / 返回。"""
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": user_msg}]
    steps = []
    client, model = get_client()
    for _ in range(max_calls):
        txt = client.chat.completions.create(
            model=model, messages=msgs, temperature=0).choices[0].message.content
        calls = parse_calls(txt)
        if not calls:
            return txt, steps
        results = []
        for call in calls:
            args = call.get("args") or []
            if not isinstance(args, list):
                steps.append({"model": txt.strip(), "tool": call.get("tool"), "args": args,
                              "result": "参数格式错误"})
                results.append("参数格式错误")
                continue
            try:
                result = TOOLS[call["tool"]](*args)
            except Exception as e:  # noqa: BLE001
                result = "工具执行失败：%s" % e
            steps.append({"model": txt.strip(), "tool": call["tool"], "args": args,
                          "result": str(result)})
            results.append("%s(%s) → %s" % (call["tool"], ", ".join(map(str, args)), result))
        msgs += [{"role": "assistant", "content": txt},
                 {"role": "user", "content": "工具返回：%s。请据此继续。" % "；".join(results)}]
    # 到上限强制收口，避免无限循环
    final = client.chat.completions.create(
        model=model, messages=msgs, temperature=0).choices[0].message.content
    return final, steps


DEMO = [
    "现在几点了？",
    "“把”这个词是 HSK 几级？",
    "现在几点？顺便算一下 (12+8)*3，再查“把”是几级。",
]


def _fmt_trace(i, q, ans, steps):
    lines = ["## 轨迹 %d" % i, "", "**问句**：%s" % q, ""]
    if not steps:
        lines += ["**模型输出**：（直接回答，未调用工具）", "",
                  "**工具返回**：无", ""]
    prev = None
    for s in steps:
        if s["model"] != prev:
            lines += ["**模型输出**：", "", "```json", s["model"], "```", ""]
            prev = s["model"]
        lines += ["**工具返回**：`%s(%s)` → `%s`" % (s["tool"], ", ".join(map(str, s["args"])), s["result"]), ""]
    lines += ["**最终回答**：%s" % ans.strip(), "", "---", ""]
    return lines


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        ans, steps = run(" ".join(args))
        print("问句：", " ".join(args))
        for s in steps:
            print("工具：%s(%s) → %s" % (s["tool"], ", ".join(map(str, s["args"])), s["result"]))
        print("回答：", ans)
        return

    out = ["# 工具调用轨迹（tool_trace.md）", "",
           "- 工具：get_time / calc / hsk_level",
           "- 记录字段：问句 / 模型输出 / 工具返回 / 最终回答",
           "- 轨迹 3 里模型一次输出了 3 个调用，程序按顺序执行后把结果一起回喂，再让模型收口", ""]
    for i, q in enumerate(DEMO, 1):
        ans, steps = run(q)
        print("Q%d: %s" % (i, q))
        for s in steps:
            print("   %s(%s) -> %s" % (s["tool"], ", ".join(map(str, s["args"])), s["result"]))
        out += _fmt_trace(i, q, ans, steps)

    # 越权表达式演示：必须被拒绝并留下记录
    bad = "__import__('os').system('dir')"
    bad_result = calc(bad)
    print("越权表达式：", bad, "->", bad_result)
    out += ["## 安全记录：越权表达式", "",
            "**输入**：`%s`" % bad,
            "**返回值**：`%s`" % bad_result,
            "**审计记录**：`%s`" % json.dumps(REJECTED, ensure_ascii=False), ""]

    Path(HERE / "tool_trace.md").write_text("\n".join(out), encoding="utf-8")
    print("已写入 tool_trace.md；拒绝记录 %d 条" % len(REJECTED))


if __name__ == "__main__":
    main()
