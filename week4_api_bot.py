# W4 命令行学科问答机器人（API 版）
# 依赖：pip install openai python-dotenv
# 运行：python week4_api_bot.py "把字句的教学难点有哪些"
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weekpath  # noqa: E402  加载 .env

weekpath.load_env()

import openai  # noqa: E402

BASE_URL = "https://api.deepseek.com/v1"          # 通义：https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL = "deepseek-chat"                            # 通义：qwen-plus

_client = None


def get_client():
    """按需创建客户端：这样"没配密钥"能在 __main__ 里被友好提示，
    而不是在 import 阶段就抛出看不懂的 OpenAIError。"""
    global _client
    if _client is None:
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key:
            raise RuntimeError("未配置 DEEPSEEK_API_KEY")
        _client = openai.OpenAI(base_url=BASE_URL, api_key=key)  # 密钥必须来自环境变量
    return _client

def ask(messages_list, temperature=0.7, max_tokens=800):
    r = get_client().chat.completions.create(
        model=MODEL,
        messages=messages_list,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    content = r.choices[0].message.content
    usage = r.usage # 获取 token 使用情况
    return content, usage
    # 注意：参数从 question 变成了 messages_list (历史消息列表)
    r = get_client().chat.completions.create(
        model=MODEL,
        messages=messages_list, # 直接把历史列表传进去
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return r.choices[0].message.content

if __name__ == "__main__":
    # ... 前面的密钥检查保留 ...
    
    # 初始化一个空的历史记录列表
    chat_history = []
    print("机器人已启动！输入 'quit' 或 'exit' 退出。")

    while True:
        # 获取用户输入
        q = input("\n你: ")
        if q.lower() in ['quit', 'exit']:
            print("再见！")
            break

        # 1. 把用户的话加入历史
        chat_history.append({"role": "user", "content": q})

        try:
                 # 下面这些全部要往右缩进一级
            # 2. 把整个历史发给 AI
            content, usage = ask(chat_history)
            
            # 3. 把 AI 的回答也加入历史
            chat_history.append({"role": "assistant", "content": content})
            
            print(f"AI: {content}")
            print(f"--- 消耗提示: 输入 {usage.prompt_tokens} 词, 输出 {usage.completion_tokens} 词 ---")
            
            # 日志记录保持不变...
            with open(weekpath.root_path("chat_log.txt"), "a", encoding="utf-8") as f:
                f.write("Q: %s\nA: %s\n\n" % (q, content))
                
        except openai.APITimeoutError:  # 注意 except 要和 try 对齐
            print("错误：请求超时...")
            chat_history.pop()

