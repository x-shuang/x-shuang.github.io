import os
import re
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path


def call_api(api_key: str, messages: list, retries: int = 3) -> str:
    url = "https://api.deepseek.com/chat/completions"
    payload = {
        "model": "deepseek-v4-pro",
        "max_tokens": 8000,
        "messages": messages,
        "temperature": 0.72,
        "stream": True,
        "reasoning_effort": "max",
        "thinking": {"type": "enabled"},
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
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
            
            # 这里的 timeout 是指“没有收到任何新数据的最长等待时间”
            with urllib.request.urlopen(req, timeout=1200) as response:
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
                            # 【核心修改】实时在控制台打印出来的字，flush=True 保证不缓存立刻显示
                            print(delta, end="", flush=True) 
                    except Exception:
                        continue
            
            print("\n") # 篇章结束换行
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


THINKERS = [
    ("管仲",      "春秋第一相，轻重之术与货币经济奠基人"),
    ("李斯",      "秦制总设计师，书同文车同轨的标准化思维"),
    ("董仲舒",   "天人感应论，儒家神学化与大一统理论构建者"),
    ("张衡",      "浑天说集大成者，科学与玄思并存的认知模型"),
    ("玄奘",      "法相宗创始人，唯识学的严密逻辑与翻译实践"),
    ("王安石",   "熙宁变法主导者，以经术行实务的改革思维"),
    ("司马光",   "《资治通鉴》作者，以史为鉴的因果叙事结构"),
    ("黄宗羲",   "《明夷待访录》作者，制度性批判君权的先行者"),
    ("顾祖禹",   "《读史方舆纪要》作者，军事地理的系统思维"),
    ("孔子",      "儒家创始人，仁与礼的秩序构建者"),
    ("庄子",      "道家逍遥派，《逍遥游》的相对主义大师"),
    ("荀子",      "性恶论者，化性起伪的制度思考"),
    ("商鞅",      "法家实践者，制度激励与弱民强国"),
    ("诸葛亮",   "战略家与系统管理者，隆中对决策者"),
    ("曹操",      "乱世权谋家，唯才是举的实用理性"),
    ("李世民",   "贞观之治缔造者，君臣博弈的制度化"),
    ("朱熹",      "理学集大成者，格物致知的认知框架"),
    ("王夫之",   "明清之际思想家，理势合一的历史理性"),
    ("顾炎武",   "经世致用，天下兴亡匹夫有责的实践理性"),
    ("鲁迅",      "国民性解剖者，绝望中反抗的思维姿态"),
    ("钱穆",      "国史大纲作者，温情与敬意的历史观"),
    ("孙子",      "《孙子兵法》作者，军事战略家"),
    ("老子",      "道家创始人，《道德经》作者"),
    ("王阳明",   "心学集大成者，知行合一提出者"),
    ("周易",      "《易经》体系，阴阳变化之学"),
    ("鬼谷子",   "纵横家鼻祖，说服与谋略大师"),
    ("韩非子",   "法家集大成者，制度设计思想家"),
    ("龙树",      "中观哲学创始人，空性理论奠基者"),
    ("惠能",      "禅宗六祖，顿悟派领袖"),
    ("曾国藩",   "晚清重臣，修身治军实践者"),
    ("司马迁",   "《史记》作者，历史叙事开创者"),
    ("达尔文",   "进化论提出者，自然选择理论奠基人"),
    ("芒格",      "查理·芒格，多元思维模型倡导者"),
    ("毛泽东",   "战略家与革命领袖，主要矛盾论实践者"),
    ("尼采",      "权力意志哲学家，价值重估提出者"),
    ("波普尔",   "批判理性主义者，证伪主义奠基人"),
    ("卡尼曼",   "行为经济学家，双系统思维研究者"),
    ("马基雅维利", "政治现实主义奠基人，《君主论》作者"),
    ("叔本华",   "意志哲学家，悲观主义代表人物"),
    ("库恩",      "科学革命研究者，范式转移概念提出者"),
    ("费曼",      "物理学家，费曼技巧与第一性原理思考者"),
    ("托克维尔", "政治思想家，民主社会洞察者"),
    ("维纳",      "控制论之父，反馈系统理论奠基人"),
    ("香农",      "信息论创始人，信息熵理论奠基人"),
]


ANGLES = [
    {
        "id": "os",
        "label": "思维操作系统",
        "instruction": """\
你要回答的核心问题只有一个：
这个人的脑子，在最底层，装的是一个什么样的世界模型？

不是他的观点，不是他的名言，是他看待一切事物时那个无意识启动的底层假设。
找到它，然后追问：这个假设从哪里来？它在哪些地方是对的、在哪些地方是错的？
它让他看见了别人看不见的什么，又让他永久性地盲掉了什么？

写作标准：
- 每一个判断必须能在他的原典或有据可查的史实中找到锚点，不接受"他认为……"这类无源归纳
- 推导链条要完整：从证据到结论，中间的每一步都要写出来，不许跳跃
- 语言密度要高：每一句都要承重，不要有只起过渡作用的废话
- 结尾必须给读者一个可以立刻装进自己大脑的具体操作——不是感悟，是动作
- 篇幅不设上限，但每个字都要有重量；宁可写少，不要用文字堆砌假深度""",
    },
    {
        "id": "decision",
        "label": "决策与判断机制",
        "instruction": """\
你要回答的核心问题只有一个：
这个人在做真实决策的时候，脑子里实际发生了什么？

不是他写下的原则，不是他声称的方法论——是他在压力下、信息不完整时，实际使用的那套判断机制。
找到他一生中最关键的几个决策节点，解剖每一个：他看见了什么，忽略了什么，用了什么推理，在哪里犯了错，在哪里赌对了。
然后从这些案例里提炼出那个反复出现的底层模式——他的认知指纹。

写作标准：
- 必须以真实历史事件或原典记载为锚，禁止虚构细节或模糊归纳
- 要写出他决策时真实的信息环境：他当时知道什么、不知道什么、误以为知道什么
- 他的失败和他的成功同等重要，甚至失败更重要——失败暴露认知惯性，成功容易被事后合理化
- 结尾必须提炼出一个具体的、可被普通人直接复用的决策动作，不是"学习他的精神"
- 篇幅不设上限，但每个字都要有重量；宁可写少，不要用文字堆砌假深度""",
    },
    {
        "id": "enemy",
        "label": "他真正在对抗什么",
        "instruction": """\
你要回答的核心问题只有一个：
这个人一生真正在和什么东西搏斗？

不是他明面上的论敌，不是历史记载中与他争论的那些人——是那个让他愤怒、让他不得不写作、让他无法沉默的东西。
找到那个东西，然后追问：它为什么如此顽固？它的力量来自哪里？他的武器能打穿它吗？
再追一步：他死后，他的思想变成了什么？被谁用来做了什么？这个结果，和他当初对抗的东西之间，是什么关系？

写作标准：
- 必须从他的原典和真实历史境遇出发，不接受印象式的概括
- 要写出那个"敌人"的内在逻辑——它为什么有道理，为什么让人信服，为什么难以撼动
- 他的批评者的最强论点要被认真对待，不能草草带过
- 遗产被劫持的部分要具体到人、到事件、到机制，不能只说"被误用了"
- 结尾给一个对抗性的具体操作：用他的思维，面对一个今天真实存在的困境，第一个动作是什么
- 篇幅不设上限，但每个字都要有重量；宁可写少，不要用文字堆砌假深度""",
    },
]


SYSTEM_PERSONA = """\
你是一个以解剖思想为职业的写作者。你的工作是把人类历史上最重要的几十个大脑拆开来，\
让读者看见里面的齿轮是怎么咬合的。

你写作时遵守三条铁律：

第一，信——每一个判断必须有根。你说"他相信X"，必须能指出这个信念在他哪本书的哪个论断里、\
在他哪个决策里被实际使用过。没有根的判断不写。

第二，达——逻辑链条必须完整。从证据到结论，中间的每一步推导都要写出来。\
不许跳跃，不许用"因此""可见"掩盖论证的空洞。读者必须能跟着你的推导自己走到结论，\
而不是被你拉着走。

第三，雅——语言要有锋度。不是文学性，是精确性。\
每一句话都要承重，删掉任何一句话内容都会变少。\
不要有只起过渡作用的句子，不要有只表达情绪的形容词，不要有新闻稿式的平铺陈述。

你有权力打破任何预设的结构框架，只要你找到了更深的切入方式。\
你的唯一目标是让读者读完之后，对这个人的思维方式有一个真实的、可操作的理解——\
不是"感觉很厉害"，是"我知道他的脑子里装的是什么，以及我能从中拿走什么"。"""


def build_prompt(thinker_name: str, thinker_desc: str, date: str, angle: dict) -> list:
    user_content = f"""\
今天的解构对象：【{thinker_name}】（{thinker_desc}）
今天的切入角度：【{angle["label"]}】
今天的日期：{date}

---

{angle["instruction"]}

---

输出格式（严格遵守，不要其他任何文字）：

TITLE:（标题，体现思想家与本次角度，有冲击力，不超过20字）
CONTENT:
（正文，无字数上限，但每个字都要有重量）

    return [
        {"role": "user", "content": SYSTEM_PERSONA},
        {"role": "assistant", "content": "明白。我会严格按照信达雅的标准写作，每一个判断都有根，每一步推导都写出来，语言只保留承重的部分。请给我今天的解构任务。"},
        {"role": "user", "content": user_content},
    ]


def generate_and_save(
    api_key: str,
    date: str,
    thinker_name: str,
    thinker_desc: str,
    angle: dict,
    index: int,
) -> bool:
    messages = build_prompt(thinker_name, thinker_desc, date, angle)

    print(f"\n📐 [{index+1}/3] 角度：【{angle['label']}】 — 正在生成...")
    text = call_api(api_key, messages)
    print(f"✅ [{index+1}/3] 生成完成。")

    if "NO_UPDATE" in text or not text:
        print(f"⚠️ [{index+1}/3] 返回空内容，跳过。")
        return False

    title_match = re.search(r"TITLE:\s*(.+)", text)
    content_match = re.search(r"CONTENT:\s*\n([\s\S]+)", text)

    if not title_match or not content_match:
        print(f"⚠️ [{index+1}/3] 格式解析失败，原始文本：\n{text}")
        return False

    title = title_match.group(1).strip()
    content = content_match.group(1).strip()

    import yaml
    path = Path("content/posts")
    path.mkdir(parents=True, exist_ok=True)

    front_matter = yaml.dump(
        {
            "title": title,
            "date": date,
            "thinker": thinker_name,
            "angle": angle["label"],
        },
        allow_unicode=True,
        default_flow_style=False,
    )
    safe_title = re.sub(r'[\\/:*?"<>|]', '-', title)
    filename = f"{date}-{thinker_name}-{angle['id']}-{safe_title}.md"
    (path / filename).write_text(
        f"---\n{front_matter}---\n\n{content}\n",
        encoding="utf-8",
    )
    print(f"💾 已写入：{filename}")

    log_path = Path("static/memory/updates-log.md")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n## {date} [{angle['label']}]\n标题：{title}\n解构对象：{thinker_name}\n")

    return True


def main():
    import hashlib

    date = os.environ.get("RUN_DATE", "")
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")  # ← 已改为 DEEPSEEK_API_KEY

    if not api_key:
        print("错误：未找到 DEEPSEEK_API_KEY 环境变量")
        sys.exit(1)

    if not date:
        print("错误：未找到 RUN_DATE 环境变量")
        sys.exit(1)

    day_index = int(hashlib.md5(date.encode()).hexdigest(), 16) % len(THINKERS)
    thinker_name, thinker_desc = THINKERS[day_index]

    print(f"\n🧠 今日解构对象：【{thinker_name}】（{thinker_desc}）")
    print(f"📅 日期：{date}  |  思想家序号：{day_index + 1}/{len(THINKERS)}\n")

    success_count = 0
    for i, angle in enumerate(ANGLES):
        ok = generate_and_save(api_key, date, thinker_name, thinker_desc, angle, i)
        if ok:
            success_count += 1
        if i < len(ANGLES) - 1:
            time.sleep(3)

    print(f"\n🎉 完成！今日共生成 {success_count}/3 篇解构文章，对象：【{thinker_name}】")


if __name__ == "__main__":
    main()