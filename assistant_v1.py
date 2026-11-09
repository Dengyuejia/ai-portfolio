# W8 阶段项目一：学科智能问答助手 v1.0
#
# 组装 = W2 提示词思路 + W6 双引擎 + W7 知识库问答
# 用法：
#   python assistant_v1.py "HSK4 累计词汇量是多少"
#   python assistant_v1.py --no-rag "把字句的教学难点有哪些"
#   python assistant_v1.py -i                 # 交互模式，输入 q 退出
#   python assistant_v1.py --prefer api "..." # 云端优先，失败自动回退本地

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import rag_qa  # noqa: E402
from llm import LLM  # noqa: E402

SYSTEM_HINT = (
    "你是国际中文教学助手，面向 HSK3–4 学习者。"
    "回答先给结论，再给简要依据；资料中没有的内容就如实说“资料中未提及”，不要编造。"
)

llm = LLM()


def answer(question, use_rag=True, prefer="local"):
    """返回 (回答, 出处列表)。use_rag=False 时只走模型本身。"""
    sources = []
    if use_rag:
        docs = rag_qa.retrieve(question)
        sources = [d["source"] for d in docs]
        prompt = SYSTEM_HINT + "\n\n" + rag_qa.build_prompt(question, docs)
    else:
        prompt = SYSTEM_HINT + "\n\n问题：" + question
    text = llm.ask(prompt, prefer=prefer, temperature=0, max_tokens=600)
    return text, sources


def show(question, use_rag=True, prefer="local"):
    t0 = time.time()
    print("Q:", question)
    try:
        text, sources = answer(question, use_rag=use_rag, prefer=prefer)
        print("A:", text.strip())
        if sources:
            print("出处:", "；".join(sources))
        print("模式:", "RAG" if use_rag else "直答", "| 耗时: %.1fs" % (time.time() - t0))
    except Exception as e:  # 常见：Ollama 没启动 / 没 pull nomic-embed-text / 没配云端密钥
        print("A: [运行失败] %s: %s" % (type(e).__name__, e))
    print("-" * 60)


def main():
    ap = argparse.ArgumentParser(description="学科智能问答助手 v1.0")
    ap.add_argument("question", nargs="*", help="要问的问题")
    ap.add_argument("--no-rag", action="store_true", help="不查资料，直接问模型")
    ap.add_argument("--prefer", default="local", choices=["local", "api"], help="优先用哪个引擎")
    ap.add_argument("-i", "--interactive", action="store_true", help="交互模式")
    args = ap.parse_args()

    if args.interactive:
        print("输入问题，回车提问；输入 q 退出。")
        while True:
            q = input("> ").strip()
            if q.lower() in ("q", "quit", "exit"):
                break
            if q:
                show(q, use_rag=not args.no_rag, prefer=args.prefer)
        return

    if not args.question:
        # 默认演示：教学法题直答，标准数字题查资料
        demo = [
            ("把字句的教学难点有哪些", False),
            ("HSK4 累计词汇量是多少", True),
            ("《愚公移山》可以设计什么课堂活动", False),
        ]
        for q, use_rag in demo:
            show(q, use_rag=(use_rag and not args.no_rag), prefer=args.prefer)
        return

    show(" ".join(args.question), use_rag=not args.no_rag, prefer=args.prefer)


if __name__ == "__main__":
    main()
