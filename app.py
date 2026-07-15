import os
import re
from bisect import bisect_right

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K = 4

ENGLISH_STOP_WORDS = {
    "a", "an", "and", "are", "do", "does", "for", "how", "in", "is",
    "of", "the", "to", "what", "when", "where", "which", "who", "why",
}
CHINESE_STOP_WORDS = {
    "一下", "主要", "什么", "介绍", "内容", "可以", "哪些", "如何",
    "怎么", "是否", "请问", "这个", "问题", "文档",
}


load_dotenv()

st.set_page_config(page_title="智能 PDF 知识库问答助手", layout="wide")

st.title("智能 PDF 知识库问答助手")

st.session_state.setdefault("messages", [])
st.session_state.setdefault("active_file", None)

uploaded_file = st.file_uploader("上传一个 PDF 文件", type=["pdf"])

if uploaded_file:
    file_identity = (uploaded_file.name, uploaded_file.size)
    if st.session_state.active_file != file_identity:
        st.session_state.active_file = file_identity
        st.session_state.messages = []
elif st.session_state.active_file is not None:
    st.session_state.active_file = None
    st.session_state.messages = []
with st.form("question_form"):
    question = st.text_input("请输入你想问 PDF 的问题")
    submitted = st.form_submit_button("提交问题", type="primary")

def extract_pdf_pages(file):
    reader = PdfReader(file)

    if reader.is_encrypted:
        raise ValueError("PDF is encrypted")

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        pages.append(
            {
                "page": page_number,
                "lines": lines,
                "text": "\n".join(lines),
            }
        )

    return pages


def build_pdf_text(pages):
    page_sections = []

    for page in pages:
        numbered_lines = "\n".join(
            f"{line_number}: {line}"
            for line_number, line in enumerate(page["lines"], start=1)
        )
        page_sections.append(f"--- 第 {page['page']} 页 ---\n{numbered_lines}")

    return "\n\n".join(page_sections)


def split_pdf_pages(pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []

    for page in pages:
        page_text = page["text"]
        if not page_text:
            continue

        line_offsets = []
        position = 0
        for line in page["lines"]:
            line_offsets.append(position)
            position += len(line) + 1

        start = 0
        while start < len(page_text):
            end = min(start + chunk_size, len(page_text))
            raw_chunk_text = page_text[start:end]
            chunk_text = raw_chunk_text.strip()

            if chunk_text:
                leading_space = len(raw_chunk_text) - len(raw_chunk_text.lstrip())
                trailing_space = len(raw_chunk_text) - len(raw_chunk_text.rstrip())
                content_start = start + leading_space
                content_end = end - trailing_space

                chunks.append(
                    {
                        "id": len(chunks) + 1,
                        "page": page["page"],
                        "start_line": bisect_right(line_offsets, content_start),
                        "end_line": bisect_right(line_offsets, content_end - 1),
                        "text": chunk_text,
                    }
                )

            if end == len(page_text):
                break

            start = end - overlap

    return chunks


def extract_keywords(text):
    normalized_text = text.lower()
    keywords = set()

    for word in re.findall(r"[a-z0-9]+", normalized_text):
        if len(word) > 1 and word not in ENGLISH_STOP_WORDS:
            keywords.add(word)

    for sequence in re.findall(r"[\u4e00-\u9fff]+", normalized_text):
        if len(sequence) == 2 and sequence not in CHINESE_STOP_WORDS:
            keywords.add(sequence)
        elif len(sequence) > 2:
            for index in range(len(sequence) - 1):
                keyword = sequence[index:index + 2]
                if keyword not in CHINESE_STOP_WORDS:
                    keywords.add(keyword)

    return keywords


def retrieve_relevant_chunks(chunks, question, top_k=TOP_K):
    keywords = extract_keywords(question)
    scored_chunks = []

    for chunk in chunks:
        chunk_text = chunk["text"].lower()
        matched_keywords = [
            keyword for keyword in keywords if keyword in chunk_text
        ]
        score = sum(len(keyword) for keyword in matched_keywords)

        if question.lower() in chunk_text:
            score += len(question) * 2

        if score > 0:
            scored_chunks.append({**chunk, "score": score})

    if not scored_chunks:
        return [{**chunk, "score": 0} for chunk in chunks[:top_k]]

    scored_chunks.sort(key=lambda chunk: (-chunk["score"], chunk["id"]))
    return scored_chunks[:top_k]


def build_context(chunks):
    return "\n\n".join(
        (
            f"[来源：第 {chunk['page']} 页，第 {chunk['start_line']}-"
            f"{chunk['end_line']} 行，文本块 {chunk['id']}]\n{chunk['text']}"
        )
        for chunk in chunks
    )


def ask_ai(context_text, user_question):
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        return "还没有配置 DEEPSEEK_API_KEY。你可以先完成 PDF 上传和文字提取，下一步我们再接入 AI。"

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )

    prompt = f"""
你是一个严谨的 PDF 文档助手。
请只根据下面通过关键词检索找到的 PDF 文本块回答用户问题。
如果这些文本块中没有答案，请说：文档中没有找到相关信息。
回答关键信息时，请在对应句子末尾标注来源，格式为：[第 X 页，第 Y-Z 行]。
只能使用文本块中提供的页码和行号，不要编造来源。

检索到的 PDF 文本块：
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

        return f"AI 服务暂时不可用，请稍后再试。错误信息：{e}"


if submitted and not uploaded_file:
    st.warning("请先上传一个 PDF 文件。")

if uploaded_file:
    try:
        with st.spinner("正在读取 PDF..."):
            pdf_pages = extract_pdf_pages(uploaded_file)
            pdf_text = build_pdf_text(pdf_pages)
    except Exception as e:
        error_text = str(e).lower()

        if "encrypt" in error_text or "password" in error_text:
            st.error("这个 PDF 已加密，请先解除密码保护后再上传。")
        else:
            st.error("PDF 读取失败，请确认文件没有损坏，并且是有效的 PDF 文件。")

        st.stop()

    if not pdf_text.strip():
        st.warning("没有从 PDF 中提取到文字。这个 PDF 可能是扫描版，后面需要加入 OCR。")
    else:
        text_chunks = split_pdf_pages(pdf_pages)
        st.success(f"PDF 读取成功，已分成 {len(text_chunks)} 个文本块")
        st.caption("行号根据 PDF 提取后的文本计算，可能与复杂排版中的视觉行号略有差异。")

        with st.expander("查看提取到的 PDF 文本"):
            st.text_area("PDF 文本", pdf_text[:5000], height=300)

        if submitted:
            if not question.strip():
                st.warning("请输入问题后再提交。")
            else:
                question_text = question.strip()
                relevant_chunks = retrieve_relevant_chunks(
                    text_chunks, question_text
                )
                context_text = build_context(relevant_chunks)
                st.session_state.messages.append(
                    {"role": "user", "content": question_text}
                )

                with st.spinner("AI 正在思考..."):
                    answer = ask_ai(context_text, question_text)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": relevant_chunks,
                    }
                )

        if st.session_state.messages:
            st.subheader("聊天记录")

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

                    sources = message.get("sources", [])
                    if sources:
                        with st.expander(
                            f"查看检索到的 {len(sources)} 个文本块"
                        ):
                            for source in sources:
                                if source.get("page"):
                                    if source["start_line"] == source["end_line"]:
                                        source_location = (
                                            f"第 {source['page']} 页，"
                                            f"第 {source['start_line']} 行"
                                        )
                                    else:
                                        source_location = (
                                            f"第 {source['page']} 页，"
                                            f"第 {source['start_line']}-"
                                            f"{source['end_line']} 行"
                                        )
                                else:
                                    source_location = "旧记录未保存页码"

                                st.markdown(
                                    f"**{source_location}，文本块 {source['id']}，"
                                    f"匹配分数 {source['score']}**"
                                )
                                st.write(source["text"])

            if st.button("清空聊天记录"):
                st.session_state.messages = []
                st.rerun()
