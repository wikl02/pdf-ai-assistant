from dotenv import load_dotenv
import streamlit as st

from config import SUPPORTED_FILE_TYPES
from document_loader import (
    build_file_infos,
    extract_document_units,
    make_file_set_id,
    safe_collection_name,
)
from llm_client import ask_ai, build_context
from text_splitter import build_preview_text, format_location, split_units_to_chunks
from vector_store import index_chunks_in_chroma, retrieve_relevant_chunks


load_dotenv()

st.set_page_config(page_title="企业知识库智能助手", layout="wide")
st.title("企业知识库智能助手")

st.session_state.setdefault("messages", [])
st.session_state.setdefault("active_knowledge_base", None)


uploaded_files = st.file_uploader(
    "上传知识库文档",
    type=SUPPORTED_FILE_TYPES,
    accept_multiple_files=True,
)

file_infos = build_file_infos(uploaded_files)

if file_infos:
    file_set_id = make_file_set_id(file_infos)
    if st.session_state.active_knowledge_base != file_set_id:
        st.session_state.active_knowledge_base = file_set_id
        st.session_state.messages = []
else:
    file_set_id = None
    if st.session_state.active_knowledge_base is not None:
        st.session_state.active_knowledge_base = None
        st.session_state.messages = []

with st.form("question_form"):
    question = st.text_input("请输入你想问知识库的问题")
    submitted = st.form_submit_button("提交问题", type="primary")

if submitted and not file_infos:
    st.warning("请先上传至少一个知识库文档。")

if file_infos:
    try:
        with st.spinner("正在解析知识库文档..."):
            document_units = []
            for file_info in file_infos:
                document_units.extend(extract_document_units(file_info))

            text_chunks = split_units_to_chunks(document_units)

    except Exception as e:
        error_text = str(e).lower()

        if "encrypt" in error_text or "password" in error_text:
            st.error("文档读取失败：其中一个 PDF 已加密，请解除密码保护后再上传。")
        else:
            st.error("文档读取失败，请确认文件没有损坏，并且格式受支持。")

        st.stop()

    if not text_chunks:
        st.warning("没有从文档中提取到可检索文本。扫描版 PDF 后续需要加入 OCR。")
    else:
        collection_name = safe_collection_name(file_set_id)

        with st.spinner("正在写入 Chroma 向量数据库..."):
            collection = index_chunks_in_chroma(collection_name, text_chunks)

        st.success(
            f"知识库构建成功：{len(file_infos)} 个文档，"
            f"{len(text_chunks)} 个文本块，已写入 Chroma。"
        )
        st.caption("PDF 行号基于提取后的文本计算，可能与复杂排版中的视觉行号略有差异。")

        with st.expander("查看已上传文档"):
            st.table(
                [
                    {
                        "文档名": file_info["name"],
                        "格式": file_info["type"],
                        "大小 KB": round(file_info["size"] / 1024, 1),
                    }
                    for file_info in file_infos
                ]
            )

        with st.expander("查看提取到的知识库文本"):
            st.text_area("知识库文本预览", build_preview_text(text_chunks), height=300)

        if submitted:
            if not question.strip():
                st.warning("请输入问题后再提交。")
            else:
                question_text = question.strip()
                relevant_chunks = retrieve_relevant_chunks(collection, question_text)
                st.session_state.messages.append(
                    {"role": "user", "content": question_text}
                )

                if relevant_chunks:
                    context_text = build_context(relevant_chunks)
                    with st.spinner("AI 正在思考..."):
                        answer = ask_ai(context_text, question_text)
                else:
                    answer = (
                        "没有在知识库中检索到与问题相关的内容，"
                        "因此本次没有调用 AI。请换一种问法，或确认文档中是否包含相关信息。"
                    )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": relevant_chunks,
                    }
                )

        if st.session_state.messages:
            st.subheader("聊天记录")

            chat_rounds = [
                st.session_state.messages[index:index + 2]
                for index in range(0, len(st.session_state.messages), 2)
            ]

            for chat_round in reversed(chat_rounds):
                for message in chat_round:
                    with st.chat_message(message["role"]):
                        st.write(message["content"])

                        sources = message.get("sources", [])
                        if sources:
                            with st.expander(f"查看检索到的 {len(sources)} 个文本块"):
                                for source in sources:
                                    metadata = source["metadata"]
                                    source_location = format_location(metadata)

                                    st.markdown(
                                        f"**{metadata['source_name']}，{source_location}，"
                                        f"文本块 {metadata['chunk_id']}，"
                                        f"相似度 {source['score']}**"
                                    )
                                    st.write(source["text"])

            if st.button("清空聊天记录"):
                st.session_state.messages = []
                st.rerun()
