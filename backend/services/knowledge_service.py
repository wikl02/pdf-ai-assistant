"""兼容接口使用的 RAG 编排：文件建库、向量检索和 AI 回答。"""

import logging

from fastapi import HTTPException

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


logger = logging.getLogger("pdf_ai_assistant.knowledge")


def build_file_info(file_name: str, file_bytes: bytes) -> dict:
    file_type = get_file_extension(file_name)
    if file_type not in SUPPORTED_FILE_TYPES:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式：{file_type}")
    return {
        "name": file_name,
        "type": file_type,
        "bytes": file_bytes,
        "hash": sha256_bytes(file_bytes),
        "size": len(file_bytes),
    }


def build_knowledge_base(file_infos: list[dict]) -> dict:
    try:
        document_units = []
        for file_info in file_infos:
            document_units.extend(extract_document_units(file_info))
        chunks = split_units_to_chunks(document_units)
    except Exception as exc:
        logger.exception("document parse failed")
        error_text = str(exc).lower()
        if "encrypt" in error_text or "password" in error_text:
            raise HTTPException(status_code=400, detail="文档读取失败：其中一个 PDF 已加密") from exc
        raise HTTPException(
            status_code=400,
            detail="文档读取失败，请确认文件没有损坏且格式受支持",
        ) from exc
    if not chunks:
        raise HTTPException(status_code=400, detail="没有从文档中提取到可检索文本")

    # 文件集合指纹决定 collection 名，相同文件集合可稳定对应同一知识库。
    collection_name = safe_collection_name(make_file_set_id(file_infos))
    index_chunks_in_chroma(collection_name, chunks)
    return {
        "collection_id": collection_name,
        "document_count": len(file_infos),
        "chunk_count": len(chunks),
        "documents": [
            {"name": item["name"], "type": item["type"], "size": item["size"]}
            for item in file_infos
        ],
    }


def answer_question(collection_id: str, question: str) -> dict:
    normalized_question = question.strip()
    if not normalized_question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    collection = get_chroma_collection(collection_id)
    if collection.count() == 0:
        raise HTTPException(status_code=404, detail="未找到对应知识库，请先上传文档")
    # 先检索再调用大模型，既减少 token 消耗，也避免模型脱离文档自由发挥。
    relevant_chunks = retrieve_relevant_chunks(collection, normalized_question)
    if not relevant_chunks:
        # 没有达到相似度阈值时直接返回，不消耗 DeepSeek 额度。
        return {
            "answer": "没有在知识库中检索到与问题相关的内容，因此本次没有调用 AI。",
            "sources": [],
            "llm_model": None,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
    llm_result = ask_ai(build_context(relevant_chunks), normalized_question)
    return {
        **llm_result,
        "sources": relevant_chunks,
    }
