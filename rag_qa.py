# W7 RAG 学科知识库问答器
#
# 课堂四步：准备文本 → 分块/向量化/入库 → 检索 → 拼接提示词交给 llm.ask()
#
# 本版没有用 langchain/chromadb：分块、余弦检索、索引持久化都用标准库 + numpy 自己写，
# 嵌入模型仍然是课程要求的 nomic-embed-text（走 Ollama 的 /api/embed）。
# 好处是依赖少、离线机器也能跑；坏处是要自己管索引文件（index/ 目录，已 gitignore）。
#
# 进阶项（二选一里的第一项）：给每个片段记来源，答案末尾附出处。
#
# 用法：
#   python rag_qa.py "HSK4 累计要求掌握多少语法点？"
#   python rag_qa.py "HSK4 累计词汇量" --prefer api
#   python rag_qa.py --rebuild "..."

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = HERE / "data.txt"                 # 等级标准节选
INDEX_DIR = HERE / "index"               # chunks.json + vectors.npy
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

BASE = (os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
if not BASE.startswith("http"):
    BASE = "http://" + BASE


def _post(path, payload, timeout=120):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def embed(texts):
    """调用本地嵌入模型，返回归一化后的向量矩阵。"""
    try:
        d = _post("/api/embed", {"model": EMBED_MODEL, "input": texts})
        vecs = np.array(d["embeddings"], dtype=np.float32)
    except urllib.error.HTTPError:
        # 老版本 Ollama 只有 /api/embeddings，一次一条
        vecs = np.array(
            [_post("/api/embeddings", {"model": EMBED_MODEL, "prompt": t})["embedding"] for t in texts],
            dtype=np.float32,
        )
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.maximum(norms, 1e-8)


def _cell(x):
    """"1000/3245" → "1000（累计 3245）"，让弱模型也能读对。"""
    if "/" in x:
        a, b = x.split("/", 1)
        return "%s（累计 %s）" % (a, b)
    return x


HSK_TAG = {
    "一级": "HSK1／HSK一级", "二级": "HSK2／HSK二级", "三级": "HSK3／HSK三级",
    "四级": "HSK4／HSK四级", "五级": "HSK5／HSK五级", "六级": "HSK6／HSK六级",
    "七—九级": "HSK7-9／HSK七至九级", "—": "全部级别合计",
}


def load_chunks(path=DATA):
    """按文档结构切块：表格一行一块，等次描述一段一块，其余按空行分段。

    表格行会改写成一句完整的话（含 HSK 对应级别和"累计"字样），
    这样检索到的片段本身就能直接回答数字题，不依赖模型去读表格。
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    chunks, i = [], 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue

        # 表头跳过
        if s.startswith("等次") and "级别" in s:
            i += 1
            continue

        # 表格行：等次 级别 音节 汉字 词汇 语法点
        parts = [p for p in re.split(r"\s{2,}", s) if p]
        if s.split(" ")[0] in ("初等", "中等", "高等", "总计") and len(parts) >= 6:
            level = parts[1]

            def add(x):
                if "/" in x:
                    a, b = x.split("/", 1)
                    return "新增 %s、累计 %s" % (a, b)
                return "%s（全部级别累计）" % x

            text = (
                "《等级标准》语言量化指标·%s%s（%s）：音节 %s；汉字 %s；词汇 %s；语法点 %s。"
                % (parts[0], level, HSK_TAG.get(level, level),
                   add(parts[2]), add(parts[3]), add(parts[4]), add(parts[5]))
            )
            chunks.append({"text": text, "title": "%s%s量化指标" % (parts[0], level)})
            i += 1
            continue

        # 等次总体描述：从"初等："开头，收到空行或下一个大标题
        if s[:3] in ("初等：", "中等：", "高等："):
            buf = [s]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^[一二三四五]、", lines[i].strip()):
                buf.append(lines[i].strip())
                i += 1
            text = "\n".join(buf)
            chunks.append({"text": text, "title": buf[0][:6] + "总体描述"})
            # 把"完成 X 阶段的学习，应掌握……"这段数字单独切出来，避免被长描述稀释
            m = re.search(r"完成(初等|中等|高等)阶段的学习", text)
            if m and m.start() > 0:
                num_text = text[m.start():].strip()
                chunks[-1]["text"] = text[: m.start()].strip()
                chunks.append({"text": num_text, "title": m.group(1) + "阶段量化要求"})
            continue

        # 其余：按空行分段（遇到"初等：/中等：/高等："或下一个大标题就停，
        # 否则"三、各等次总体描述"会把初等整段吞掉）
        buf = [s]
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and not re.match(r"^(初等|中等|高等)：", lines[i].strip())
            and not re.match(r"^[一二三四五]、", lines[i].strip())
        ):
            buf.append(lines[i].strip())
            i += 1
        chunks.append({"text": "\n".join(buf), "title": s[:16]})

    return chunks


def build_index(force=False):
    INDEX_DIR.mkdir(exist_ok=True)
    meta_p, vec_p = INDEX_DIR / "chunks.json", INDEX_DIR / "vectors.npy"
    if not force and meta_p.exists() and vec_p.exists():
        return json.loads(meta_p.read_text(encoding="utf-8")), np.load(vec_p)
    chunks = load_chunks()
    t0 = time.time()
    # 向量里带上标题（"初等阶段量化要求"这种级别词），否则短问句容易只匹配到相近的级别
    vecs = embed([c["title"] + "：" + c["text"] for c in chunks])
    meta_p.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    np.save(vec_p, vecs)
    print("[建库] %d 段，用时 %.1fs，模型 %s" % (len(chunks), time.time() - t0, EMBED_MODEL))
    return chunks, vecs


KEYWORDS = ["初等", "中等", "高等", "一级", "二级", "三级", "四级", "五级", "六级",
            "七级", "八级", "九级", "词汇", "词语", "汉字", "音节", "语法点", "HSK"]


def retrieve(question, k=3, rebuild=False):
    """混合检索：向量余弦 + 领域关键词加权。

    nomic-embed-text 对中文的区分度一般，"初等/中等"这种只差一个词的片段
    容易排错，所以再用问题里出现的关键词给候选加一点分。
    """
    chunks, vecs = build_index(rebuild)
    q = embed([question])[0]
    scores = vecs @ q
    order = np.argsort(-scores)[: max(k * 4, 12)]
    q_terms = [w for w in KEYWORDS if w in question]
    ranked = []
    for i in order:
        kw = sum(1 for w in q_terms if w in chunks[i]["title"] or w in chunks[i]["text"])
        ranked.append((float(scores[i]) + 0.05 * kw, i))
    ranked.sort(reverse=True)
    return [
        {"text": chunks[i]["text"], "source": "data.txt·" + chunks[i]["title"], "score": round(s, 3)}
        for s, i in ranked[:k]
    ]


def build_prompt(question, docs):
    ctx = "\n\n".join("[%d] %s" % (i + 1, d["text"]) for i, d in enumerate(docs))
    return (
        "你是国际中文教师。请只根据下面的资料回答问题，答案里的数字必须出自资料，不要自己编。\n"
        "如果资料里确实找不到答案，就回答“资料中未提及”。\n\n"
        "资料：\n%s\n\n问题：%s\n\n"
        "回答格式：第一行给结论，第二行写“依据：[编号] 资料里的原句”。" % (ctx, question)
    )


def _get_llm():
    for p in (HERE, HERE.parent, HERE.parent / "week06", HERE.parent / "week06_双引擎"):
        if (p / "llm.py").is_file():
            sys.path.insert(0, str(p))
            break
    from llm import LLM

    return LLM()


def rag_qa(question, llm=None, prefer="local", k=3, **kw):
    docs = retrieve(question, k)
    llm = llm or _get_llm()
    answer = llm.ask(build_prompt(question, docs), prefer=prefer, **kw)
    cited = [i for i in range(1, len(docs) + 1) if "[%d]" % i in answer] or list(range(1, len(docs) + 1))
    sources = [docs[i - 1]["source"] for i in cited]
    return answer, sources


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    rebuild = "--rebuild" in sys.argv
    prefer = "api" if "--prefer" in sys.argv and "api" in sys.argv else "local"
    question = " ".join(args) or "HSK4 累计要求掌握多少语法点？"

    docs = retrieve(question, rebuild=rebuild)
    print("【检索片段】")
    for i, d in enumerate(docs, 1):
        print("  [%d] %s（相似度 %.3f）\n      %s" % (i, d["source"], d["score"], d["text"][:80].replace("\n", " ")))
    print("---")
    answer, sources = rag_qa(question, prefer=prefer)
    print(answer)
    print("\n【出处】" + "；".join(sources))


if __name__ == "__main__":
    main()
