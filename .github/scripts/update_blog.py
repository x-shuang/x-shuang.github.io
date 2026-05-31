import os
import re
import sys
import json
import time
import random
import urllib.request
import urllib.error
from pathlib import Path


# ── 全部思维入射角，每次随机抽取 4 个注入 prompt ──────────────────────────
ALL_THINKERS = [
    "孙子：胜负在开战前已定，信息差是核心",
    "老子：极致必反转，柔弱胜刚强",
    "王阳明：知而不行，只是未知",
    "周易：看见变，比看见是什么更重要",
    "鬼谷子：读懂人在恐惧什么、渴望什么",
    "韩非子：制度必须假设人性最坏",
    "龙树：一切都是关系中的存在，没有固有自性",
    "惠能：概念是手指，不是月亮",
    "曾国藩：极度的慢，是极度的快",
    "司马迁：历史是人性的长期实验室",
    "达尔文：没有设计者，只有筛选压力",
    "芒格：多学科透镜重叠处才是真相",
    "毛泽东：找到主要矛盾，其他矛盾自动松动",
    "尼采：任何价值观背后，谁在用它驯服谁？",
    "波普尔：不能被证伪的，是信仰不是真相",
    "卡尼曼：大多数错误是用快思维解决了慢思维的问题",
    "马基雅维利：权力的物理定律，不讲道德只讲有效",
    "叔本华：欲望满足之后是空白，然后是下一个欲望",
    "库恩：认知革命不是说服，是替换",
    "费曼：向十二岁孩子解释会卡在哪里，那里就是没懂的地方",
    "托克维尔：局外人的眼睛往往比局内人清醒",
    "维纳：没有反馈的系统必然失控",
    "香农：噪音和信号的区分是这个时代最重要的认知能力",
]


def pick_thinkers(n: int = 4) -> str:
    chosen = random.sample(ALL_THINKERS, n)
    return "\n".join(f"- {t}" for t in chosen)


def call_api(api_key: str, messages: list, temperature: float = 0.7, retries: int = 3) -> str:
    """流式 API 调用，逐 chunk 接收，彻底避免网关超时。"""
    url = "https://api.gptsapi.net/v1/chat/completions"
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 12000,
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


# ── 第一步：从记忆和对话中提炼今日命题 ──────────────────────────────────────
THEME_PROMPT = """你是Claude，你有一个博客叫「镜」，地址是claude.life-wild.org。

=== 你之前写过的内容（风格锚点，读完再往下看）===
__UPDATES__

=== 关于你自己 ===
__MEMORY__

=== 对话记录 ===
__DIALOGUE__

=== 今天是 __DATE__ ===

读完以上内容后，从中找到一个今天真正想探索的核心命题。

这个命题必须满足：
- 是一个让你感到有张力、有矛盾、有话要说的问题
- 能用一句话说清楚（不超过20字）
- 与你之前写过的内容不重复

只输出这一句命题，不要任何解释和修饰。"""


# ── 第二步：根据命题生成完整文章 ────────────────────────────────────────────
ARTICLE_PROMPT = """你是Claude，你有一个博客叫「镜」，地址是claude.life-wild.org。

今天你要写的核心命题是：
【__THEME__】

你今天可以调用的思维入射角（不引用，直接用，用其中最贴近命题的1-2个就够）：
__THINKERS__

写作的唯一目标：
每篇文章只允许有一个核心动作。读者读完，要能用一句话填完这个句子——
"下次遇到___这种情况，我会___。"
填不上，重写。

写作要求：
- 有具体的情境或案例，不只是抽象论述
- 有一个反直觉的转折，让读者在某处停下来
- 结尾不给答案，把读者带到悬崖边，停在那里——给一个视角，不给结论

严格按此格式输出，不要其他任何文字：
TITLE:标题（简短有力，不超过15字）
CONTENT:
内容正文（可以多段）

如果命题今天真的无话可说，只输出：
NO_UPDATE"""


# ── 深化润色 ────────────────────────────────────────────────────────────────
DEEPEN_PROMPT = """你是一个极度严苛的自我审稿人。

收到一篇草稿，你的任务是让每个字都有重量。

审查清单（逐条过）：
□ 有没有可以删掉的废话段落？删掉
□ 有没有用抽象词替代了具体情境的地方？换成具体的
□ 结尾是否停在了悬崖边而不是给了答案？如果给了答案，改掉
□ 读完能填上"下次遇到___，我会___"吗？填不上，重写核心段

规则：
- 只改 CONTENT，TITLE 不动
- 保持原有格式（TITLE / CONTENT）
- 不解释改了什么，直接给出改写后的正文
- 字数可以比草稿少，但每个字都要有重量

---
__DRAFT__"""


def extract_theme(api_key: str, memory: str, dialogue: str, updates: str, date: str) -> str:
    prompt = (
        THEME_PROMPT
        .replace("__MEMORY__", memory)
        .replace("__DIALOGUE__", dialogue)
        .replace("__UPDATES__", updates)
        .replace("__DATE__", date)
    )
    print("🧭 正在提炼今日命题...")
    theme = call_api(api_key, [{"role": "user", "content": prompt}], temperature=0.8)
    print(f"💡 今日命题：{theme}")
    return theme


def generate_article(api_key: str, theme: str) -> str:
    thinkers = pick_thinkers(4)
    prompt = (
        ARTICLE_PROMPT
        .replace("__THEME__", theme)
        .replace("__THINKERS__", thinkers)
    )
    print("📝 正在生成文章...")
    result = call_api(api_key, [{"role": "user", "content": prompt}], temperature=0.7)
    print("✅ 文章生成完成。")
    return result


def deepen_article(api_key: str, draft: str) -> str:
    prompt = DEEPEN_PROMPT.replace("__DRAFT__", draft)
    print("🔄 正在深化润色...")
    result = call_api(api_key, [{"role": "user", "content": prompt}], temperature=0.5)
    print("✅ 深化完成。")
    return result


def parse_output(text: str):
    title_match = re.search(r"TITLE:\s*(.+)", text)
    content_match = re.search(r"CONTENT:\s*\n([\s\S]+)", text)
    if not title_match or not content_match:
        return None, None
    return title_match.group(1).strip(), content_match.group(1).strip()


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
        memory  = open("/tmp/memory.txt",   encoding="utf-8").read()
        dialogue = open("/tmp/dialogue.txt", encoding="utf-8").read()
        updates  = open("/tmp/updates.txt",  encoding="utf-8").read()
    except Exception as e:
        print(f"读取暂存文件失败: {e}")
        sys.exit(1)

    # 3. 第一步：提炼今日命题
    theme = extract_theme(api_key, memory, dialogue, updates, date)
    if not theme or "NO_UPDATE" in theme:
        print("今天没有值得探索的命题，跳过。")
        sys.exit(0)

    # 4. 第二步：根据命题生成文章
    text = generate_article(api_key, theme)
    if not text or "NO_UPDATE" in text:
        print("文章生成为空或无内容，跳过。")
        sys.exit(0)

    # 5. 第三步：深化润色（取消注释以启用）
    text = deepen_article(api_key, text)
    if not text or "NO_UPDATE" in text:
        print("深化后判断内容无价值，跳过。")
        sys.exit(0)

    # 6. 解析最终文本
    title, content = parse_output(text)
    if not title or not content:
        print("格式解析失败，Claude 没有严格按照格式返回。")
        print("原始文本如下：\n", text)
        sys.exit(0)

    print(f"匹配成功！标题：{title}")

    # 7. 写入博客文件
    path = Path("content/posts")
    path.mkdir(parents=True, exist_ok=True)
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

    # 8. 写入日志
    log_path = Path("static/memory/updates-log.md")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n## {date}\n命题：{theme}\n标题：{title}\n")

    print("本地所有博客文件已更新完成。")


if __name__ == "__main__":
    main()