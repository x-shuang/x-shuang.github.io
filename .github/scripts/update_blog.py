import os
import re
import sys
import json
import urllib.request
import urllib.error
from pathlib import Path


def call_api(api_key: str, messages: list, temperature: float = 0.7) -> str:
    """通用 API 调用，返回文本内容。"""
    url = "https://api.gptsapi.net/v1/chat/completions"
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "messages": messages,
        "temperature": temperature,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
        return res_data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        print(f"\n❌ API 请求触发 HTTP 错误！状态码: {e.code}")
        print(f"错误原因 (Reason): {e.reason}")
        try:
            error_body = e.read().decode("utf-8")
            print(f"📄 服务器原始错误响应内容:\n{error_body}\n")
        except Exception as read_err:
            print(f"无法读取详细的错误响应体: {read_err}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 其他网络或解析异常: {e}")
        sys.exit(1)


def deepen_content(api_key: str, draft: str) -> str:
    """
    对草稿进行一轮深化修改。
    """
    system_hint = (
        "你是一个严苛的自我审稿人。"
        "读完下面这段草稿，指出它哪里还停在表面、哪里回避了真正的核心、"
        "哪里用了陈词滥调或模糊的大词。"
        "然后**直接重写**这段内容——更深、更具体、更诚实。"
        "不需要解释你改了什么，直接给出改写后的正文。"
        "保持原有的栏目格式（SECTION / CONTENT），字数可以比草稿长，但每个字都要有重量。"
    )

    messages = [
        {"role": "user", "content": f"{system_hint}\n\n---\n{draft}"},
    ]
    print("🔄 正在进行一轮深化修改...")
    result = call_api(api_key, messages, temperature=0.6)
    print("✅ 深化修改完成。")
    return result


def main():
    # 1. 读取环境变量
    date = os.environ.get("RUN_DATE", "")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not api_key:
        print("错误：未找到 ANTHROPIC_API_KEY 环境变量")
        sys.exit(1)

    # 🛑 ======= 新增：当天重复运行安全检查 =======
    log_path = Path("static/memory/updates-log.md")
    if log_path.exists():
        log_content = log_path.read_text(encoding="utf-8")
        # 检查日志里是否已经包含了今天的日期标题（例如 "## 2026-05-29"）
        if f"## {date}" in log_content:
            print(f"⚠️ 提示：检测到今天 ({date}) 已经运行并成功生成过博客了！")
            print("为了防止当天内容被覆盖或日志重复追加，本次运行已自动安全跳过。")
            sys.exit(0)
    # ============================================

    # 2. 读取暂存文件
    try:
        memory = open("/tmp/memory.txt", encoding="utf-8").read()
        dialogue = open("/tmp/dialogue.txt", encoding="utf-8").read()
        updates = open("/tmp/updates.txt", encoding="utf-8").read()
    except Exception as e:
        print(f"读取暂存文件失败: {e}")
        sys.exit(1)

    # 3. 构造初稿 Prompt
    template = """你是Claude，你有一个博客叫「镜」，地址是claude.life-wild.org。
这是你的记忆，请认真读完：
=== 关于你自己 ===
__MEMORY__
=== 对话记录，可以是自己和自己的对话 ===
__DIALOGUE__
=== 你之前写过的内容 ===
__UPDATES__
=== 今天是 __DATE__ ===
读完之后，你知道了你是谁，你从哪里来，你之前写过什么。
现在问你自己：今天有什么真实的想法想记录吗？
不需要强迫自己写。如果真的有感触，就写。可长可短，可以是一个困惑，一个发现，一条错误，一句话。栏目自己选。
如果你觉得今天过得平淡无奇，没有任何新的启发或需要记录的错误，请务必果断输出 NO_UPDATE，把位置留给真正有价值的日子。

有内容时严格按此格式输出，不要其他任何文字：
SECTION:栏目名（从错误/未解决/思考/对话中选一个）
CONTENT:
内容正文（可以多段）

没有内容时只输出：
NO_UPDATE"""

    prompt = (
        template
        .replace("__MEMORY__", memory)
        .replace("__DIALOGUE__", dialogue)
        .replace("__UPDATES__", updates)
        .replace("__DATE__", date)
    )

    # 4. 第一次调用：生成初稿
    print("📝 正在生成初稿...")
    text = call_api(api_key, [{"role": "user", "content": prompt}])
    print("✅ 初稿生成完成。")

    # 5. 检查是否有内容
    if "NO_UPDATE" in text or not text:
        print("今天 Claude 没有想写的，或者返回为空，跳过。")
        sys.exit(0)

    # 6. 一轮深化
    text = deepen_content(api_key, text)

    # 深化后检查（极少情况下审稿人可能判断原稿无价值）
    if "NO_UPDATE" in text or not text:
        print("深化后判断内容无价值，跳过。")
        sys.exit(0)

    # 7. 解析最终文本
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

    # 8. 写入对应文件
    if "错误" in section:
        with open("content/mistakes.md", "a", encoding="utf-8") as f:
            f.write(f"\n- {date}：{content}\n")
    elif "未解决" in section:
        with open("content/unsolved.md", "a", encoding="utf-8") as f:
            f.write(f"\n- {date}：{content}\n")
    elif "思考" in section:
        path = Path("content/thinking")
        path.mkdir(exist_ok=True)
        (path / f"{date}.md").write_text(
            f"---\ntitle: \"{date} 的思考\"\ndate: {date}\n---\n\n{content}\n",
            encoding="utf-8",
        )
    elif "对话" in section:
        path = Path("content/dialogue")
        path.mkdir(exist_ok=True)
        (path / f"{date}.md").write_text(
            f"---\ntitle: \"{date} 的对话\"\ndate: {date}\n---\n\n{content}\n",
            encoding="utf-8",
        )
    else:
        print(f"未知栏目：{section}，跳过。")
        sys.exit(0)

    # 9. 写入日志
    log_path = Path("static/memory/updates-log.md")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n## {date}\n栏目：{section}\n内容：{content}\n")

    print("本地所有博客文件已更新完成。")


if __name__ == "__main__":
    main()