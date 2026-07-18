from openai import OpenAI

from settings import get_secret_value
from text_splitter import format_location


def build_context(chunks):
    context_sections = []

    for chunk in chunks:
        metadata = chunk["metadata"]
        location = format_location(metadata)
        context_sections.append(
            (
                f"[来源：{metadata['source_name']}，{location}，"
                f"文本块 {metadata['chunk_id']}]\n{chunk['text']}"
            )
        )

    return "\n\n".join(context_sections)


def get_deepseek_api_key():
    return get_secret_value("DEEPSEEK_API_KEY")


def ask_ai(context_text, user_question):
    api_key = get_deepseek_api_key()

    if not api_key:
        return "还没有配置 DEEPSEEK_API_KEY。你可以先完成知识库上传和检索，下一步再接入 AI。"

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    prompt = f"""
你是一个严谨的企业知识库问答助手。
请只根据下面通过 Chroma 向量数据库检索到的知识库文本块回答用户问题。
如果这些文本块中没有答案，请说：文档中没有找到相关信息。
回答关键信息时，请在对应句子末尾标注来源，格式为：[文档名，第 X 页/第 X 行/第 X 段]。
只能使用文本块中提供的来源信息，不要编造来源。

检索到的知识库文本块：
{context_text[:12000]}

用户问题：
{user_question}
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content

    except Exception as e:
        error_text = str(e).lower()

        if "402" in error_text or "insufficient balance" in error_text or "balance" in error_text:
            return "当前 DeepSeek 账户余额不足，请充值后重试，或更换可用的 API Key。"

        if "401" in error_text or "authentication" in error_text or "api key" in error_text:
            return "DeepSeek API Key 无效或未授权，请检查 .env 文件中的 DEEPSEEK_API_KEY。"

        if "429" in error_text or "rate limit" in error_text:
            return "当前请求过于频繁，触发了 DeepSeek 限流，请稍后再试。"

        if "500" in error_text or "503" in error_text or "server" in error_text or "overloaded" in error_text:
            return "DeepSeek 服务暂时繁忙，请稍后再试。"

        if "timeout" in error_text or "connection" in error_text:
            return "连接 DeepSeek 服务失败，请检查网络后重试。"

        return "AI 服务暂时不可用，请稍后再试。"
