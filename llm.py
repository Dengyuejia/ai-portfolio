# W6 双引擎封装 —— 此后所有周统一经此调用
#
# 作业 1 的增强项：调用耗时与费用估算打印（三选一里的第 3 项）。
# 为什么选它：本周要交边界测试记录，四列里有一列就是"耗时"；云端调用还要知道花多少钱。
# 多轮对话、失败重试不是不重要，只是等第 8 周做助手、第 9 周做工具调用时再加更自然。
#
# 接口约定（后面几周都按这个用）：
#   from llm import LLM
#   LLM().ask("问题", prefer="local")   # 本地优先，失败自动切云端
#   LLM().ask("问题", prefer="api")     # 云端优先，失败自动切本地
#
# 只依赖标准库 + openai 包（本地调用用 urllib，省掉 requests 依赖）。

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def _load_env():
    """没有 python-dotenv 也能读 .env：只看当前目录、脚本目录、上一级目录。"""
    if os.getenv("DEEPSEEK_API_KEY"):
        return
    here = Path(__file__).resolve().parent
    for p in (Path.cwd() / ".env", here / ".env", here.parent / ".env"):
        if not p.is_file():
            continue
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        break


_load_env()


def _post_json(url, payload, timeout=60):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class LocalEngine:
    """本地引擎（Ollama）：隐私任务优先、断网可用。"""

    name = "local"

    def __init__(self, model=None, base_url=None):
        self.model = model or os.getenv("LOCAL_MODEL", "qwen2.5:0.5b")
        self.base_url = (base_url or os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        if not self.base_url.startswith("http"):
            self.base_url = "http://" + self.base_url
        self.last_usage = {"prompt": 0, "completion": 0}
        self.last_truncated = False

    def ask(self, prompt, temperature=0.7, max_tokens=800):
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "stream": False,
        }
        d = _post_json(self.base_url + "/api/chat", payload, timeout=60)
        self.last_usage = {
            "prompt": d.get("prompt_eval_count", 0),
            "completion": d.get("eval_count", 0),
        }
        self.last_truncated = d.get("done_reason") == "length"
        return d["message"]["content"]


class APIEngine:
    """云端引擎：复杂任务、本地失败兜底。

    注意：openai.OpenAI(...) 在 api_key 为 None 时会直接抛错。若在构造 LLM 时就建客户端，
    没配密钥的同学连"纯本地"模式都跑不起来。所以改成**按需创建**：第一次真正调云端才建。
    """

    name = "api"
    PRICE_IN = 2.0   # 元 / 百万 token，deepseek-chat 量级示意，以官网为准
    PRICE_OUT = 8.0

    def __init__(self, base_url=None, model=None):
        self.base_url = base_url or "https://api.deepseek.com/v1"
        self.model = model or "deepseek-chat"
        self._client = None
        self.last_usage = {"prompt": 0, "completion": 0}
        self.last_truncated = False
        self.last_cost = 0.0

    def _get_client(self):
        if self._client is None:
            key = os.getenv("DEEPSEEK_API_KEY")
            if not key:
                raise RuntimeError(
                    "未配置 DEEPSEEK_API_KEY：复制 .env.example 为 .env 并填入密钥；"
                    "只想用本地时请调用 ask(..., prefer='local')。"
                )
            import openai
            self._client = openai.OpenAI(base_url=self.base_url, api_key=key)
        return self._client

    def ask(self, prompt, temperature=0.7, max_tokens=800):
        r = self._get_client().chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        u = r.usage
        self.last_usage = {
            "prompt": getattr(u, "prompt_tokens", 0),
            "completion": getattr(u, "completion_tokens", 0),
        }
        self.last_cost = (
            self.last_usage["prompt"] / 1e6 * self.PRICE_IN
            + self.last_usage["completion"] / 1e6 * self.PRICE_OUT
        )
        self.last_truncated = getattr(r.choices[0], "finish_reason", "") == "length"
        return r.choices[0].message.content


class LLM:
    """统一入口：ask(prompt, prefer=...)。

    prefer='local'：本地挂了自动切云端；
    prefer='api'  ：云端挂了（断网/超时/没密钥）自动切本地。
    两侧对称，任何一边失败都不让程序直接崩——这就是双引擎的意义。
    """

    def __init__(self, local_model=None):
        self.local = LocalEngine(local_model)
        self.api = APIEngine()

    def _report(self, engine, text, seconds):
        u = engine.last_usage
        cost = getattr(engine, "last_cost", 0.0)
        cut = " | 可能被截断" if engine.last_truncated else ""
        print(
            "[引擎] %s | 耗时 %.2fs | 输入 %d / 输出 %d token | 费用约 ¥%.4f%s"
            % (engine.name, seconds, u["prompt"], u["completion"], cost, cut)
        )

    def ask(self, prompt, prefer="local", **kw):
        if prefer == "local":
            chain = [(self.local, "本地失败，切换云端"), (self.api, "云端失败，切换本地")]
        else:
            chain = [(self.api, "云端失败，切换本地"), (self.local, "本地失败，切换云端")]

        errors = []
        for engine, tag in chain:
            t0 = time.time()
            try:
                text = engine.ask(prompt, **kw)
            except Exception as e:  # 不吞异常：一定要打印原因
                errors.append("%s: %s" % (type(e).__name__, e))
                print("[回退] %s：%s: %s" % (tag, type(e).__name__, e))
                continue
            self._report(engine, text, time.time() - t0)
            return text
        raise RuntimeError("本地和云端都不可用（" + "；".join(errors) + "）")


if __name__ == "__main__":
    llm = LLM()
    print(llm.ask("给《愚公移山》出一道 HSK4 阅读理解题，附答案。", prefer="local"))
