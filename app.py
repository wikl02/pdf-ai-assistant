import os

from dotenv import load_dotenv
import requests
import streamlit as st

from config import SUPPORTED_FILE_TYPES
from text_splitter import format_location


load_dotenv()

DEFAULT_API_BASE_URL = "http://localhost:8000"
API_BASE_URL = os.getenv("FASTAPI_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")

st.set_page_config(page_title="企业知识库智能助手", layout="wide")
st.title("企业知识库智能助手")

st.session_state.setdefault("access_token", "")
st.session_state.setdefault("current_username", "")
st.session_state.setdefault("collection_id", "")
st.session_state.setdefault("uploaded_documents", [])
st.session_state.setdefault("chunk_count", 0)
st.session_state.setdefault("messages", [])


def api_headers():
    return {"Authorization": f"Bearer {st.session_state.access_token}"}


def parse_error_message(response):
    try:
        detail = response.json().get("detail")
        if isinstance(detail, str):
            return detail
        return str(detail)
    except Exception:
        return response.text or "请求失败，请稍后再试。"


def require_backend_login():
    if st.session_state.access_token:
        with st.sidebar:
            st.success(f"已登录：{st.session_state.current_username}")
            st.caption(f"后端地址：{API_BASE_URL}")
            if st.button("退出登录"):
                st.session_state.access_token = ""
                st.session_state.current_username = ""
                st.session_state.collection_id = ""
                st.session_state.uploaded_documents = []
                st.session_state.chunk_count = 0
                st.session_state.messages = []
                st.rerun()
        return

    st.subheader("账号登录")
    st.caption("当前页面会调用 FastAPI 后端完成登录、上传和问答。")

    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录", type="primary")

    if submitted:
        if not username.strip() or not password:
            st.warning("请输入用户名和密码。")
        else:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/login",
                    json={"username": username.strip(), "password": password},
                    timeout=15,
                )
            except requests.RequestException:
                st.error("无法连接 FastAPI 后端。请确认后端已启动：python -m uvicorn backend.main:app --reload --port 8000")
                st.stop()

            if response.status_code == 200:
                data = response.json()
                st.session_state.access_token = data["access_token"]
                st.session_state.current_username = username.strip()
                st.rerun()
            else:
                st.error(parse_error_message(response))

    st.stop()


require_backend_login()

with st.sidebar:
    if st.button("检查后端状态"):
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=10)
            if response.status_code == 200:
                st.success("FastAPI 后端运行正常")
            else:
                st.error(f"后端异常：{response.status_code}")
        except requests.RequestException:
            st.error("无法连接 FastAPI 后端")

uploaded_files = st.file_uploader(
    "上传知识库文档",
    type=SUPPORTED_FILE_TYPES,
    accept_multiple_files=True,
)

if uploaded_files:
    if st.button("构建知识库", type="primary"):
        files = []
        for uploaded_file in uploaded_files:
            files.append(
                (
                    "files",
                    (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type or "application/octet-stream",
                    ),
                )
            )

        try:
            with st.spinner("正在调用 FastAPI 后端构建知识库..."):
                response = requests.post(
                    f"{API_BASE_URL}/upload",
                    headers=api_headers(),
                    files=files,
                    timeout=180,
                )
        except requests.RequestException:
            st.error("上传失败：无法连接 FastAPI 后端。")
        else:
            if response.status_code == 200:
                data = response.json()
                st.session_state.collection_id = data["collection_id"]
                st.session_state.uploaded_documents = data["documents"]
                st.session_state.chunk_count = data["chunk_count"]
                st.session_state.messages = []
                st.success(
                    f"知识库构建成功：{data['document_count']} 个文档，"
                    f"{data['chunk_count']} 个文本块。"
                )
            else:
                st.error(parse_error_message(response))

if st.session_state.collection_id:
    st.success(
        f"当前知识库已就绪：{len(st.session_state.uploaded_documents)} 个文档，"
        f"{st.session_state.chunk_count} 个文本块。"
    )
    st.caption(f"collection_id：{st.session_state.collection_id}")

    with st.expander("查看已上传文档"):
        st.table(
            [
                {
                    "文档名": document["name"],
                    "格式": document["type"],
                    "大小 KB": round(document["size"] / 1024, 1),
                }
                for document in st.session_state.uploaded_documents
            ]
        )
else:
    st.info("请先上传文档并点击“构建知识库”。")

with st.form("question_form"):
    question = st.text_input("请输入你想问知识库的问题")
    submitted = st.form_submit_button("提交问题", type="primary")

if submitted:
    question_text = question.strip()

    if not st.session_state.collection_id:
        st.warning("请先构建知识库后再提问。")
    elif not question_text:
        st.warning("请输入问题后再提交。")
    else:
        st.session_state.messages.append({"role": "user", "content": question_text})

        try:
            with st.spinner("正在调用 FastAPI 后端检索并生成回答..."):
                response = requests.post(
                    f"{API_BASE_URL}/ask",
                    headers=api_headers(),
                    json={
                        "collection_id": st.session_state.collection_id,
                        "question": question_text,
                    },
                    timeout=180,
                )
        except requests.RequestException:
            answer = "请求失败：无法连接 FastAPI 后端。"
            sources = []
        else:
            if response.status_code == 200:
                data = response.json()
                answer = data["answer"]
                sources = data.get("sources", [])
            else:
                answer = parse_error_message(response)
                sources = []

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "sources": sources,
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
