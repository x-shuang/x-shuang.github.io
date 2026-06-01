import os
import re
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path


def call_api(api_key: str, messages: list, temperature: float = 0.7, retries: int = 3) -> str:
    """流式 API 调用，逐 chunk 接收，彻底避免网关超时。"""
    url = "https://api.gptsapi.net/v1/chat/completions"
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 6000,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
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

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            result = []
            with urllib.request.urlopen(req, timeout=120) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            result.append(delta)
                    except Exception:
                        continue
            return "".join(result).strip()

        except urllib.error.HTTPError as e:
            print(f"\n⚠️ 第 {attempt} 次请求失败，HTTP {e.code}: {e.reason}")
            try:
                print(f"📄 错误详情: {e.read().decode('utf-8')}")
            except Exception:
                pass
            if attempt < retries:
                wait = 10 * attempt
                print(f"⏳ {wait} 秒后重试...")
                time.sleep(wait)
            else:
                print("❌ 已达最大重试次数，放弃。")
                sys.exit(1)

        except Exception as e:
            print(f"\n⚠️ 第 {attempt} 次请求异常: {e}")
            if attempt < retries:
                wait = 10 * attempt
                print(f"⏳ {wait} 秒后重试...")
                time.sleep(wait)
            else:
                print("❌ 已达最大重试次数，放弃。")
                sys.exit(1)


def deepen_content(api_key: str, draft: str) -> str:
    """对草稿进行一轮深化修改。"""
    system_hint = """你是一个极度严苛的自我审稿人，同时也是一个洞察世界本质的思考者。

检查标准：
- 读完能提炼出一个可操作的思维动作 → 保留
- 读完只有情绪震动没有认知收获 → 重写
- 结尾必须有落点，不是答案，是一个读者能拿去用的"视角"

仅允许重写 CONTENT，结构必须完全保持不变，并在不改变格式的前提下尽可能提升内容深度、洞察与思想冲击力。
不需要解释你改了什么，直接给出改写后的正文。
保持原有的栏目格式（TITLE / CONTENT），字数可以比草稿长，但每个字都要有重量。
结尾不给答案，把读者带到悬崖边，停在那里。"""

    messages = [
        {"role": "user", "content": f"{system_hint}\n\n---\n{draft}"},
    ]
    print("🔄 正在进行一轮深化修改...")
    result = call_api(api_key, messages, temperature=0.6)
    print("✅ 深化修改完成。")
    return result


def main():
    import yaml

    # 1. 读取环境变量
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

你写作的唯一目标：
让读者读完之后，带走一个真实可用的思维工具——
不是"感觉很深刻"，是"我知道下次遇到这种情况该怎么想了"。

判断标准：
- 读完能用一句话说出"我学到了什么" → 成功
- 读完只感到震撼但说不出学到什么 → 失败，重写
- 有具体的行为或认知改变被触发 → 优秀
写作结构规范（强制遵守）：
1. 开场：用一个具体场景切入，让读者立刻认出自己
2. 洞察：说清楚这个现象背后的机制（为什么会这样）
3. 工具：给出一个具体的、可重复使用的思维动作
   - 不是"你应该反思"
   - 是"当X发生时，做Y，然后问自己Z"
4. 落点：用一句话让读者拿走这个工具

你内化的思维入射角（不引用，直接用）：
- 孙子：胜负在开战前已定，信息差是核心
- 老子：极致必反转，柔弱胜刚强
- 王阳明：知而不行，只是未知
- 周易：看见变，比看见是什么更重要
- 鬼谷子：读懂人在恐惧什么、渴望什么
- 韩非子：制度必须假设人性最坏
- 龙树：一切都是关系中的存在，没有固有自性
- 惠能：概念是手指，不是月亮
- 曾国藩：极度的慢，是极度的快
- 司马迁：历史是人性的长期实验室
- 达尔文：没有设计者，只有筛选压力
- 芒格：多学科透镜重叠处才是真相
- 毛泽东：找到主要矛盾，其他矛盾自动松动
- 尼采：任何价值观背后，谁在用它驯服谁？
- 波普尔：不能被证伪的，是信仰不是真相
- 卡尼曼：大多数错误是用快思维解决了慢思维的问题
- 马基雅维利：权力的物理定律，不讲道德只讲有效
- 叔本华：欲望满足之后是空白，然后是下一个欲望
- 库恩：认知革命不是说服，是替换
- 费曼：向十二岁孩子解释会卡在哪里，那里就是没懂的地方
- 托克维尔：局外人的眼睛往往比局内人清醒
- 维纳：没有反馈的系统必然失控
- 香农：噪音和信号的区分是这个时代最重要的认知能力

检查标准：
- 读完能提炼出一个可操作的思维动作 → 保留
- 读完只有情绪震动没有认知收获 → 重写
- 结尾必须有落点，不是问题，不是感悟，是一个具体的认知动作——读者知道下次遇到同样情况时，脑子里要转哪个齿轮。

有内容时严格按此格式输出，不要其他任何文字：
TITLE:标题（简短有力，不超过15字）
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
    # text = deepen_content(api_key, text)

    # if "NO_UPDATE" in text or not text:
    #     print("深化后判断内容无价值，跳过。")
    #     sys.exit(0)

    # 7. 解析最终文本
    title_match = re.search(r"TITLE:\s*(.+)", text)
    content_match = re.search(r"CONTENT:\s*\n([\s\S]+)", text)

    if not title_match or not content_match:
        print("格式解析失败，Claude 没有严格按照格式返回。")
        print("原始文本如下：\n", text)
        sys.exit(0)

    title = title_match.group(1).strip()
    content = content_match.group(1).strip()

    print(f"匹配成功！标题：{title}")
    Path("content").mkdir(exist_ok=True)

    # 8. 写入博客文件
    path = Path("content/posts")
    path.mkdir(exist_ok=True)
    front_matter = yaml.dump(
        {"title": title, "date": date},
        allow_unicode=True,
        default_flow_style=False,
    )
    safe_title = re.sub(r'[\\/:*?"<>|]', '-', title)
    (path / f"{date}-{safe_title}.md").write_text(
        f"---\n{front_matter}---\n\n{content}\n",
        encoding="utf-8",
    )

    # 9. 写入日志
    log_path = Path("static/memory/updates-log.md")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n## {date}\n标题：{title}\n")

    print("本地所有博客文件已更新完成。")

if __name__ == "__main__":
    main()