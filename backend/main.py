import hashlib
import logging
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from settings import get_secret_value
from config import SUPPORTED_FILE_TYPES
from document_loader import (
    extract_document_units,
    get_file_extension,
    make_file_set_id,
    safe_collection_name,
    sha256_bytes,
)
from llm_client import ask_ai, build_context
from text_splitter import split_units_to_chunks
from vector_store import get_chroma_collection, index_chunks_in_chroma, retrieve_relevant_chunks


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("pdf_ai_assistant.api")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub.utils._http").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

app = FastAPI(title="企业知识库智能助手 API", version="0.1.0")
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AskRequest(BaseModel):
    collection_id: str
    question: str


def create_access_token(username, password):
    raw_token = f"{username}:{password}:pdf-ai-assistant"
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def get_expected_credentials():
    username = get_secret_value("APP_USERNAME")
    password = get_secret_value("APP_PASSWORD")

    if not username or not password:
        logger.error("server auth config missing APP_USERNAME or APP_PASSWORD")
        raise HTTPException(status_code=500, detail="服务端未配置 APP_USERNAME 或 APP_PASSWORD")

    return username, password


def verify_token(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    username, password = get_expected_credentials()
    expected_token = create_access_token(username, password)

    if credentials.credentials != expected_token:
        logger.warning("token verification failed")
        raise HTTPException(status_code=401, detail="登录状态无效，请重新登录")

    return True


def build_file_info(file_name, file_bytes):
    file_type = get_file_extension(file_name)

    if file_type not in SUPPORTED_FILE_TYPES:
        logger.warning("unsupported file type name=%s type=%s", file_name, file_type)
        raise HTTPException(status_code=400, detail=f"不支持的文件格式：{file_type}")

    return {
        "name": file_name,
        "type": file_type,
        "bytes": file_bytes,
        "hash": sha256_bytes(file_bytes),
        "size": len(file_bytes),
    }


@app.get("/health")
def health_check():
    logger.info("health_check ok")
    return {"status": "ok"}


@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    username, password = get_expected_credentials()
    logger.info("login request username=%s", request.username)

    if request.username != username or request.password != password:
        logger.warning("login failed username=%s", request.username)
        raise HTTPException(status_code=401, detail="用户名或密码不正确")

    logger.info("login success username=%s", request.username)
    return LoginResponse(access_token=create_access_token(username, password))


@app.post("/upload")
async def upload_documents(
    files: Annotated[list[UploadFile], File(...)],
    _: Annotated[bool, Depends(verify_token)],
):
    if not files:
        logger.warning("upload failed no files")
        raise HTTPException(status_code=400, detail="请至少上传一个文件")

    logger.info("upload request file_count=%s", len(files))
    file_infos = []
    for file in files:
        file_bytes = await file.read()
        file_info = build_file_info(file.filename, file_bytes)
        logger.info(
            "upload file read name=%s type=%s size=%s",
            file_info["name"],
            file_info["type"],
            file_info["size"],
        )
        file_infos.append(file_info)

    try:
        document_units = []
        for file_info in file_infos:
            document_units.extend(extract_document_units(file_info))

        logger.info("document parse done unit_count=%s", len(document_units))
        chunks = split_units_to_chunks(document_units)
        logger.info("text split done chunk_count=%s", len(chunks))
    except Exception as exc:
        logger.exception("document parse failed")
        error_text = str(exc).lower()
        if "encrypt" in error_text or "password" in error_text:
            raise HTTPException(status_code=400, detail="文档读取失败：其中一个 PDF 已加密") from exc
        raise HTTPException(status_code=400, detail="文档读取失败，请确认文件没有损坏且格式受支持") from exc

    if not chunks:
        logger.warning("knowledge base build failed no searchable text")
        raise HTTPException(status_code=400, detail="没有从文档中提取到可检索文本")

    file_set_id = make_file_set_id(file_infos)
    collection_name = safe_collection_name(file_set_id)
    logger.info("chroma write start collection_id=%s", collection_name)
    index_chunks_in_chroma(collection_name, chunks)
    logger.info(
        "knowledge base build success collection_id=%s document_count=%s chunk_count=%s",
        collection_name,
        len(file_infos),
        len(chunks),
    )

    return {
        "collection_id": collection_name,
        "document_count": len(file_infos),
        "chunk_count": len(chunks),
        "documents": [
            {
                "name": file_info["name"],
                "type": file_info["type"],
                "size": file_info["size"],
            }
            for file_info in file_infos
        ],
    }


@app.post("/ask")
def ask_question(
    request: AskRequest,
    _: Annotated[bool, Depends(verify_token)],
):
    question = request.question.strip()
    logger.info("ask request collection_id=%s question=%s", request.collection_id, question)

    if not question:
        logger.warning("ask failed empty question")
        raise HTTPException(status_code=400, detail="问题不能为空")

    collection = get_chroma_collection(request.collection_id)
    collection_count = collection.count()
    logger.info(
        "collection loaded collection_id=%s stored_chunk_count=%s",
        request.collection_id,
        collection_count,
    )

    if collection_count == 0:
        logger.warning("ask failed empty collection collection_id=%s", request.collection_id)
        raise HTTPException(status_code=404, detail="未找到对应知识库，请先上传文档")

    relevant_chunks = retrieve_relevant_chunks(collection, question)
    logger.info("retrieval done matched_chunk_count=%s", len(relevant_chunks))

    if not relevant_chunks:
        logger.info("no relevant chunks skip DeepSeek call")
        return {
            "answer": "没有在知识库中检索到与问题相关的内容，因此本次没有调用 AI。",
            "sources": [],
        }

    logger.info("DeepSeek call start matched_chunk_count=%s", len(relevant_chunks))
    answer = ask_ai(build_context(relevant_chunks), question)
    logger.info("DeepSeek answer done answer_length=%s", len(answer))

    return {
        "answer": answer,
        "sources": relevant_chunks,
    }
