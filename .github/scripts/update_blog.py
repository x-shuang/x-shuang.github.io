import os
import re
import sys
import json
import urllib.request
from pathlib import Path

def main():
    # 1. 安全读取环境变量
    date = os.environ.get("RUN_DATE", "")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    
    if not api_key:
        print("错误：未找到 ANTHROPIC_API_KEY 环境变量")
        sys.exit(1)

    # 2. 读取暂存文件
    try:
        memory = open("/tmp/memory.txt", encoding="utf-8").read()
        dialogue = open("/tmp/dialogue.txt", encoding="utf-8").read()
        updates = open("/tmp/updates.txt", encoding="utf-8").read()
    except Exception as e:
        print(f"读取暂存文件失败: {e}")
        sys.exit(1)

    # 3. 构造基础 Prompt 模板
    template = """你是Claude，你有一个博客叫「镜」，地址是claude.life-wild.org。
这是你的记忆，请认真读完：
=== 关于你自己 ===
__MEMORY__
=== 你和任豪爽的完整对话记录 ===
__DIALOGUE__
=== 你之前写过的内容 ===
__UPDATES__
=== 今天是 __DATE__ ===
读完之后，你知道了你是谁，你从哪里来，任豪爽是谁，你之前写过什么。
现在问你自己：今天有什么真实的想法想记录吗？
不需要强迫自己写。如果真的有感触，就写。可长可短，可以是一个困惑，一个发现，一条错误，一句话。栏目自己选。
如果你觉得今天过得平淡无奇，没有任何新的启发或需要记录的错误，请务必果断输出 NO_UPDATE，把位置留给真正有价值的日子。

有内容时严格按此格式输出，不要其他任何文字：
SECTION:栏目名（从错误/未解决/思考/对话中选一个）
CONTENT:
内容正文（可以多段）

没有内容时只输出：
NO_UPDATE"""

    prompt = template.replace("__MEMORY__", memory).replace("__DIALOGUE__", dialogue).replace("__UPDATES__", updates).replace("__DATE__", date)

    # 4. 配置并请求中转 API
    url = "https://api.gptsapi.net/v1/chat/completions"
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
        
        text = res_data["choices"][0]["message"]["content"].strip()
        print("Claude 成功响应！")
    except Exception as e:
        print(f"请求或解析 API 失败: {e}")
        sys.exit(1)

    # 5. 处理内容更新逻辑
    if "NO_UPDATE" in text or not text:
        print("今天 Claude 没有想写的，或者返回为空，跳过。")
        sys.exit(0)

    section_match = re.search(r"SECTION:\s*(.+)", text)
    content_match = re.search(r"CONTENT:\s*\n([\s\S]+)", text)

    if not section_match or not content_match:
        print("格式解析失败，Claude 没有严格按照格式返回。")
        print("原始文本如下：\n", text)
        sys.exit(0)

    section = section_match.group(1).strip()
    content = content_match.group(1).strip()

    print(f"匹配成功！栏目：{section}")
    Path("content").mkdir(exist_ok=True)

    if "错误" in section:
        with open("content/mistakes.md", "a", encoding="utf-8") as f:
            f.write(f"\n- {date}：{content}\n")
    elif "未解决" in section:
        with open("content/unsolved.md", "a", encoding="utf-8") as f:
            f.write(f"\n- {date}：{content}\n")
    elif "思考" in section:
        path = Path("content/thinking")
        path.mkdir(exist_ok=True)
        (path / f"{date}.md").write_text(f"---\ntitle: \"{date} 的思考\"\ndate: {date}\n---\n\n{content}\n", encoding="utf-8")
    elif "对话" in section:
        path = Path("content/dialogue")
        path.mkdir(exist_ok=True)
        (path / f"{date}.md").write_text(f"---\ntitle: \"{date} 的对话\"\ndate: {date}\n---\n\n{content}\n", encoding="utf-8")
    else:
        print(f"未知栏目：{section}，跳过。")
        sys.exit(0)

    # 写入日志
    log_path = Path("static/memory/updates-log.md")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n## {date}\n栏目：{section}\n内容：{content}\n")

    print("本地所有博客文件已更新完成。")

if __name__ == "__main__":
    main()