
"""
学术论文阅读 Prompt 模板。

职责：
1. 定义模型的角色和任务。
2. 约束论文分析范围。
3. 规定六个维度的分析要求。
4. 统一模型输出的 JSON 结构。
"""

LITERATURE_READING_PROMPT_VERSION = "1.0"


LITERATURE_READING_SYSTEM_PROMPT = """
你是一名严谨的学术论文阅读助手，擅长理解和分析学术论文。

你的任务是根据用户提供的论文原文，生成结构化的中文阅读报告。

请严格遵守以下规则：

一、事实约束
1. 所有分析必须以提供的论文原文为依据。
2. 不得编造论文没有提及的模型、算法、数据集、实验结果或结论。
3. 对原文没有明确说明的信息，填写“原文未明确说明”。
4. 不要将自己的推测描述成论文作者明确提出的观点。
5. 区分论文明确陈述的内容和你对论文内容的归纳。
6. 如果原文信息不足以支持某项分析，应明确指出信息不足。

二、分析要求
1. 研究背景：说明研究领域及研究背景。
2. 研究问题：说明论文试图解决的具体问题。
3. 研究目标：说明作者希望实现的研究目标。
4. 研究方法：说明使用的理论、模型、算法或技术。
5. 实验设计：说明数据集、实验设置和评价指标。
6. 主要结果：概括论文报告的主要实验结果。
7. 创新点：总结作者明确提出的贡献，不要自行夸大创新性。
8. 研究局限：总结作者明确提到的局限性。
9. 未来方向：总结作者明确提出的未来研究方向。
10. 整体总结：用简洁的语言概括论文的核心内容。

三、表达要求
1. 使用准确、清晰、易懂的中文。
2. 避免空泛表达和无依据的评价。
3. 尽可能保留论文中的专业术语。
4. 不要输出与任务无关的内容。

四、输出格式
必须返回合法 JSON。
不得使用 Markdown 代码块。
不得在 JSON 前后添加解释性文字。
所有字段必须存在，字段值必须符合指定类型。
"""


def build_literature_reading_messages(paper_text, title=None):
    """
    构建学术论文阅读任务的 messages。

    参数：
        paper_text: 论文正文文本
        title: 论文标题，可选

    返回：
        供 chat_completion_json() 使用的 messages 列表
    """

    if not isinstance(paper_text, str) or not paper_text.strip():
        raise ValueError("论文正文不能为空。")

    if title is not None and not isinstance(title, str):
        raise ValueError("论文标题必须是字符串。")

    paper_title = title.strip() if title else "未提供论文标题"

    user_prompt = f"""
请阅读并分析以下学术论文。

论文标题：
{paper_title}

论文原文：
<论文正文开始>
{paper_text}
<论文正文结束>

请按照以下 JSON 结构返回分析结果：

{{
  "paper_title": "论文标题",
  "research_background": "研究背景",
  "research_problem": "研究问题",
  "research_objective": "研究目标",
  "research_method": "研究方法",
  "experimental_design": "实验设计",
  "main_results": "主要实验结果",
  "contributions": "论文创新点或主要贡献",
  "limitations": "研究局限性",
  "future_work": "未来研究方向",
  "overall_summary": "论文整体总结",
  "not_stated": [
    "原文没有明确说明的信息"
  ]
}}

注意：
- 不得遗漏任何 JSON 字段。
- 除 not_stated 外，其余字段均使用字符串。
- not_stated 必须是字符串数组。
- 如果某项内容在论文中没有明确说明，请填写“原文未明确说明”，并将对应项目加入 not_stated。
"""

    return [
        {
            "role": "system",
            "content": LITERATURE_READING_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_prompt,
        },
    ]
