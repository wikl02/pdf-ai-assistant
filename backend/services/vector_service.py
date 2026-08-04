"""数据库文档与 Chroma 文本块之间的同步操作。"""

from vector_store import build_embeddings, get_chroma_collection


def delete_document_chunks(collection_name: str, document_id: int) -> None:
    """只删除指定文档的文本块，不影响同一知识库中的其他文档。"""
    collection = get_chroma_collection(collection_name)
    collection.delete(where={"document_id": str(document_id)})


def index_document_chunks(collection_name: str, document_id: int, chunks: list[dict]):
    """以 document_id 为边界，安全替换一份文档的全部向量文本块。"""
    collection = get_chroma_collection(collection_name)
    delete_document_chunks(collection_name, document_id)
    if not chunks:
        return collection

    # Embedding 将文本转换为向量；tuple 也可作为底层缓存函数的键。
    chunk_texts = tuple(chunk["text"] for chunk in chunks)
    embeddings = build_embeddings(chunk_texts)
    ids = []
    metadatas = []
    for position, chunk in enumerate(chunks, start=1):
        ids.append(f"document_{document_id}_chunk_{position}")
        metadata = dict(chunk["metadata"])
        # document_id 写入 Chroma metadata，删除和重建索引时可精确过滤。
        metadata["document_id"] = str(document_id)
        metadatas.append(metadata)

    collection.add(
        ids=ids,
        documents=[chunk["text"] for chunk in chunks],
        metadatas=metadatas,
        embeddings=embeddings,
    )
    return collection
