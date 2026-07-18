from vector_store import build_embeddings, get_chroma_collection


def delete_document_chunks(collection_name: str, document_id: int) -> None:
    """Delete only chunks that belong to one document."""
    collection = get_chroma_collection(collection_name)
    collection.delete(where={"document_id": str(document_id)})


def index_document_chunks(collection_name: str, document_id: int, chunks: list[dict]):
    """Replace one document's chunks without touching other documents."""
    collection = get_chroma_collection(collection_name)
    delete_document_chunks(collection_name, document_id)
    if not chunks:
        return collection

    chunk_texts = tuple(chunk["text"] for chunk in chunks)
    embeddings = build_embeddings(chunk_texts)
    ids = []
    metadatas = []
    for position, chunk in enumerate(chunks, start=1):
        ids.append(f"document_{document_id}_chunk_{position}")
        metadata = dict(chunk["metadata"])
        metadata["document_id"] = str(document_id)
        metadatas.append(metadata)

    collection.add(
        ids=ids,
        documents=[chunk["text"] for chunk in chunks],
        metadatas=metadatas,
        embeddings=embeddings,
    )
    return collection
