"""企业知识库与文档的持久化管理服务。

上传流程为：保存原文件和数据库记录 -> 解析文本 -> 分块 -> 向量化 -> 写入 Chroma。
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.core.config import settings
from backend.models.knowledge import (
    Document,
    DocumentIndexTask,
    DocumentStatus,
    DocumentVersion,
    IndexTaskStatus,
    IndexTaskTrigger,
    KnowledgeBase,
    KnowledgeBaseDocument,
)
from backend.models.user import User
from backend.schemas.management import KnowledgeBaseCreate
from backend.services.knowledge_service import build_file_info
from backend.services.vector_service import delete_document_chunks, index_document_chunks
from document_loader import extract_document_units
from text_splitter import split_units_to_chunks


logger = logging.getLogger("pdf_ai_assistant.management")


def _knowledge_base_or_404(db: Session, knowledge_base_id: int) -> KnowledgeBase:
    # 一次预加载关联文档，避免在统计文档数和文本块数时反复查询数据库。
    knowledge_base = db.scalar(
        select(KnowledgeBase)
        .where(KnowledgeBase.id == knowledge_base_id)
        .options(
            selectinload(KnowledgeBase.document_links).selectinload(
                KnowledgeBaseDocument.document
            )
        )
    )
    if not knowledge_base:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return knowledge_base


def _document_link_or_404(
    db: Session, knowledge_base_id: int, document_id: int
) -> KnowledgeBaseDocument:
    link = db.scalar(
        select(KnowledgeBaseDocument)
        .where(
            KnowledgeBaseDocument.knowledge_base_id == knowledge_base_id,
            KnowledgeBaseDocument.document_id == document_id,
        )
        .options(
            selectinload(KnowledgeBaseDocument.knowledge_base),
            selectinload(KnowledgeBaseDocument.document),
        )
    )
    if not link:
        raise HTTPException(status_code=404, detail="知识库中不存在该文档")
    return link


def knowledge_base_to_dict(knowledge_base: KnowledgeBase) -> dict:
    documents = [link.document for link in knowledge_base.document_links]
    return {
        "id": knowledge_base.id,
        "name": knowledge_base.name,
        "description": knowledge_base.description,
        "collection_name": knowledge_base.collection_name,
        "created_by_id": knowledge_base.created_by_id,
        "document_count": len(documents),
        "chunk_count": sum(document.chunk_count for document in documents),
        "created_at": knowledge_base.created_at,
        "updated_at": knowledge_base.updated_at,
    }


def list_knowledge_bases(
    db: Session, knowledge_base_ids: set[int] | None = None
) -> list[dict]:
    statement = select(KnowledgeBase).options(
        selectinload(KnowledgeBase.document_links).selectinload(
            KnowledgeBaseDocument.document
        )
    )
    if knowledge_base_ids is not None:
        if not knowledge_base_ids:
            return []
        statement = statement.where(KnowledgeBase.id.in_(knowledge_base_ids))
    items = list(db.scalars(statement.order_by(KnowledgeBase.created_at.desc())))
    return [knowledge_base_to_dict(item) for item in items]


def create_knowledge_base(
    db: Session, payload: KnowledgeBaseCreate, current_user: User
) -> KnowledgeBase:
    name = payload.name.strip()
    if db.scalar(select(KnowledgeBase).where(KnowledgeBase.name == name)):
        raise HTTPException(status_code=409, detail="知识库名称已存在")

    knowledge_base = KnowledgeBase(
        name=name,
        description=payload.description.strip() if payload.description else None,
        # 每个数据库知识库对应一个独立的 Chroma collection。
        collection_name=f"enterprise_kb_{uuid4().hex}",
        created_by_id=current_user.id,
    )
    db.add(knowledge_base)
    db.commit()
    db.refresh(knowledge_base)
    logger.info(
        "knowledge base created id=%s collection=%s user_id=%s",
        knowledge_base.id,
        knowledge_base.collection_name,
        current_user.id,
    )
    return knowledge_base


def get_knowledge_base_detail(db: Session, knowledge_base_id: int) -> dict:
    knowledge_base = _knowledge_base_or_404(db, knowledge_base_id)
    result = knowledge_base_to_dict(knowledge_base)
    result["documents"] = [link.document for link in knowledge_base.document_links]
    return result


def list_documents(db: Session, knowledge_base_id: int) -> list[Document]:
    knowledge_base = _knowledge_base_or_404(db, knowledge_base_id)
    return sorted(
        (link.document for link in knowledge_base.document_links),
        key=lambda document: document.created_at,
        reverse=True,
    )


def _storage_path(filename: str) -> Path:
    safe_name = Path(filename).name or "document"
    suffix = Path(safe_name).suffix.lower()
    settings.upload_storage_dir.mkdir(parents=True, exist_ok=True)
    # 磁盘文件使用随机名，避免重名覆盖；原文件名仍保存在数据库中用于展示。
    return (settings.upload_storage_dir / f"{uuid4().hex}{suffix}").resolve()


def _process_document(
    db: Session,
    knowledge_base: KnowledgeBase,
    document: Document,
    trigger: IndexTaskTrigger,
    initiated_by_id: int | None,
) -> Document:
    version = db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document.id,
            DocumentVersion.version_number == document.current_version_number,
        )
    )
    task = DocumentIndexTask(
        document_id=document.id,
        knowledge_base_id=knowledge_base.id,
        version_number=document.current_version_number,
        trigger=trigger.value,
        status=IndexTaskStatus.PROCESSING.value,
        initiated_by_id=initiated_by_id,
        started_at=datetime.now(timezone.utc),
    )
    db.add(task)
    # 先落库“处理中”状态，让失败后仍能在管理页面看到并执行重新索引。
    document.status = DocumentStatus.PROCESSING.value
    document.error_message = None
    if version:
        version.status = DocumentStatus.PROCESSING.value
        version.error_message = None
    db.commit()
    started_at = perf_counter()

    try:
        # 解析器保留页码、行号、段落或表格行等来源位置，供回答引用。
        file_bytes = Path(document.storage_path).read_bytes()
        file_info = build_file_info(document.filename, file_bytes)
        units = extract_document_units(file_info)
        chunks = split_units_to_chunks(units)
        if not chunks:
            raise ValueError("没有从文档中提取到可检索文本")
        # 这里会计算 Embedding，并只替换当前文档在 collection 中的文本块。
        index_document_chunks(knowledge_base.collection_name, document.id, chunks)
    except Exception as exc:
        duration_ms = round((perf_counter() - started_at) * 1000)
        error_message = str(exc)[:1000]
        logger.exception("document indexing failed document_id=%s", document.id)
        document.status = DocumentStatus.FAILED.value
        document.chunk_count = 0
        document.error_message = error_message
        if version:
            version.status = DocumentStatus.FAILED.value
            version.chunk_count = 0
            version.error_message = error_message
        task.status = IndexTaskStatus.FAILED.value
        task.error_message = error_message
        task.duration_ms = duration_ms
        task.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"文档 {document.filename} 处理失败，请检查文件内容和格式",
        ) from exc

    document.status = DocumentStatus.READY.value
    document.chunk_count = len(chunks)
    document.error_message = None
    if version:
        version.status = DocumentStatus.READY.value
        version.chunk_count = len(chunks)
        version.error_message = None
    task.status = IndexTaskStatus.SUCCEEDED.value
    task.chunk_count = len(chunks)
    task.error_message = None
    task.duration_ms = round((perf_counter() - started_at) * 1000)
    task.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(document)
    logger.info(
        "document indexed document_id=%s knowledge_base_id=%s chunk_count=%s",
        document.id,
        knowledge_base.id,
        document.chunk_count,
    )
    return document


def upload_document(
    db: Session,
    knowledge_base_id: int,
    current_user: User,
    filename: str,
    file_bytes: bytes,
) -> Document:
    knowledge_base = _knowledge_base_or_404(db, knowledge_base_id)
    file_info = build_file_info(Path(filename).name, file_bytes)

    # SHA256 用内容而不是文件名判重，同一文件改名后仍会被识别。
    duplicate = db.scalar(
        select(Document)
        .join(KnowledgeBaseDocument)
        .where(
            KnowledgeBaseDocument.knowledge_base_id == knowledge_base_id,
            Document.sha256 == file_info["hash"],
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail=f"文档 {filename} 已存在于该知识库")

    # 原文件先持久化，再建立数据库关联；以后可以从原文件重新构建索引。
    storage_path = _storage_path(filename)
    storage_path.write_bytes(file_bytes)
    document = Document(
        filename=file_info["name"],
        file_type=file_info["type"],
        file_size=file_info["size"],
        sha256=file_info["hash"],
        storage_path=str(storage_path),
        status=DocumentStatus.PENDING.value,
        chunk_count=0,
        current_version_number=1,
        uploaded_by_id=current_user.id,
    )
    db.add(document)
    db.flush()
    db.add(
        KnowledgeBaseDocument(
            knowledge_base_id=knowledge_base.id,
            document_id=document.id,
        )
    )
    db.add(
        DocumentVersion(
            document_id=document.id,
            version_number=1,
            filename=document.filename,
            file_type=document.file_type,
            file_size=document.file_size,
            sha256=document.sha256,
            storage_path=document.storage_path,
            status=DocumentStatus.PENDING.value,
            chunk_count=0,
            created_by_id=current_user.id,
        )
    )
    db.commit()
    db.refresh(document)
    # 当前版本同步建立索引，因此较大文档或模型冷启动时请求会等待较久。
    return _process_document(
        db,
        knowledge_base,
        document,
        IndexTaskTrigger.UPLOAD,
        current_user.id,
    )


def reindex_document(
    db: Session, knowledge_base_id: int, document_id: int, current_user: User
) -> Document:
    link = _document_link_or_404(db, knowledge_base_id, document_id)
    if not Path(link.document.storage_path).is_file():
        raise HTTPException(status_code=404, detail="文档原始文件不存在，无法重新索引")
    return _process_document(
        db,
        link.knowledge_base,
        link.document,
        IndexTaskTrigger.REINDEX,
        current_user.id,
    )


def upload_document_version(
    db: Session,
    knowledge_base_id: int,
    document_id: int,
    current_user: User,
    filename: str,
    file_bytes: bytes,
) -> Document:
    link = _document_link_or_404(db, knowledge_base_id, document_id)
    document = link.document
    file_info = build_file_info(Path(filename).name, file_bytes)
    if file_info["hash"] == document.sha256:
        raise HTTPException(status_code=409, detail="新版本内容与当前版本相同")

    storage_path = _storage_path(filename)
    storage_path.write_bytes(file_bytes)
    version_number = document.current_version_number + 1
    document.filename = file_info["name"]
    document.file_type = file_info["type"]
    document.file_size = file_info["size"]
    document.sha256 = file_info["hash"]
    document.storage_path = str(storage_path)
    document.current_version_number = version_number
    document.status = DocumentStatus.PENDING.value
    document.chunk_count = 0
    document.error_message = None
    db.add(
        DocumentVersion(
            document_id=document.id,
            version_number=version_number,
            filename=document.filename,
            file_type=document.file_type,
            file_size=document.file_size,
            sha256=document.sha256,
            storage_path=document.storage_path,
            status=DocumentStatus.PENDING.value,
            chunk_count=0,
            created_by_id=current_user.id,
        )
    )
    db.commit()
    db.refresh(document)
    return _process_document(
        db,
        link.knowledge_base,
        document,
        IndexTaskTrigger.VERSION_UPLOAD,
        current_user.id,
    )


def get_document_lifecycle(
    db: Session, knowledge_base_id: int, document_id: int
) -> dict:
    link = _document_link_or_404(db, knowledge_base_id, document_id)
    versions = list(
        db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number.desc())
        )
    )
    tasks = list(
        db.scalars(
            select(DocumentIndexTask)
            .where(
                DocumentIndexTask.document_id == document_id,
                DocumentIndexTask.knowledge_base_id == knowledge_base_id,
            )
            .order_by(DocumentIndexTask.created_at.desc())
        )
    )
    return {"document": link.document, "versions": versions, "index_tasks": tasks}


def delete_document(db: Session, knowledge_base_id: int, document_id: int) -> None:
    link = _document_link_or_404(db, knowledge_base_id, document_id)
    document = link.document
    # 使用 document_id 过滤，避免删除同一 collection 中其他文档的向量。
    delete_document_chunks(link.knowledge_base.collection_name, document.id)

    # 文档可能被多个知识库关联；只有没有其他关联时才删除原文件和文档记录。
    remaining_links = db.scalar(
        select(func.count())
        .select_from(KnowledgeBaseDocument)
        .where(
            KnowledgeBaseDocument.document_id == document.id,
            KnowledgeBaseDocument.knowledge_base_id != knowledge_base_id,
        )
    )
    db.delete(link)
    delete_file = remaining_links == 0
    storage_paths = set(
        db.scalars(
            select(DocumentVersion.storage_path).where(
                DocumentVersion.document_id == document.id
            )
        )
    )
    storage_paths.add(document.storage_path)
    if delete_file:
        db.delete(document)
    db.commit()

    if delete_file:
        for value in storage_paths:
            storage_path = Path(value)
            if storage_path.is_file():
                storage_path.unlink()
    logger.info(
        "document deleted document_id=%s knowledge_base_id=%s",
        document_id,
        knowledge_base_id,
    )
