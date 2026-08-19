from openai import OpenAI

# 本模块把检索结果组织成上下文，并通过 OpenAI 兼容协议调用 DeepSeek。
from openai import AsyncOpenAI

from settings import get_secret_value
from text_splitter import format_location


def build_context(chunks):
    # 来源位置和原文一起交给模型，回答才能生成可核查的引用。
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


def _build_prompt(context_text, user_question):
    return f"""
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


def _missing_key_result():
    return {
        "answer": "还没有配置 DEEPSEEK_API_KEY。你可以先完成知识库上传和检索，下一步再接入 AI。",
        "llm_model": None,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


def _success_result(response, model_name):
    usage = response.usage
    return {
        "answer": response.choices[0].message.content or "",
        "llm_model": response.model or model_name,
        "prompt_tokens": usage.prompt_tokens if usage else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "total_tokens": usage.total_tokens if usage else None,
    }


def _error_result(error, model_name):
    # 对外返回可操作的友好提示，不把底层异常和敏感配置暴露给用户。
    error_text = str(error).lower()
    if "402" in error_text or "insufficient balance" in error_text or "balance" in error_text:
        answer = "当前 DeepSeek 账户余额不足，请充值后重试，或更换可用的 API Key。"
    elif "401" in error_text or "authentication" in error_text or "api key" in error_text:
        answer = "DeepSeek API Key 无效或未授权，请检查 .env 文件中的 DEEPSEEK_API_KEY。"
    elif "429" in error_text or "rate limit" in error_text:
        answer = "当前请求过于频繁，触发了 DeepSeek 限流，请稍后再试。"
    elif "500" in error_text or "503" in error_text or "server" in error_text or "overloaded" in error_text:
        answer = "DeepSeek 服务暂时繁忙，请稍后再试。"
    elif "timeout" in error_text or "connection" in error_text:
        answer = "连接 DeepSeek 服务失败，请检查网络后重试。"
    else:
        answer = "AI 服务暂时不可用，请稍后再试。"

    return {
        "answer": answer,
        "llm_model": model_name,
        "prompt_tokens": None,
        "completion_tokens": None,
        "total_tokens": None,
    }


def ask_ai(context_text, user_question):
    model_name = "deepseek-chat"
    api_key = get_deepseek_api_key()
    if not api_key:
        return _missing_key_result()

    # 质量评估继续使用同步客户端，保持现有批量执行逻辑不变。
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": _build_prompt(context_text, user_question)}],
            temperature=0.2,
        )
        return _success_result(response, model_name)
    except Exception as error:
        return _error_result(error, model_name)


async def ask_ai_async(context_text, user_question):
    """异步调用 DeepSeek，使聊天任务被取消时能关闭上游 HTTP 请求。"""

    model_name = "deepseek-chat"
    api_key = get_deepseek_api_key()
    if not api_key:
        return _missing_key_result()

    client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": _build_prompt(context_text, user_question)}],
            temperature=0.2,
        )
        return _success_result(response, model_name)
    except Exception as error:
        return _error_result(error, model_name)
