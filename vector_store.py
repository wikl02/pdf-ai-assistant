from functools import lru_cache

# 本模块负责 Embedding 模型加载、Chroma 持久化及向量相似度检索。
import chromadb
from sentence_transformers import SentenceTransformer

from config import CHROMA_DB_PATH, EMBEDDING_MODEL_NAME, SIMILARITY_THRESHOLD, TOP_K


@lru_cache(maxsize=1)
def load_embedding_model():
    # 模型较大且加载较慢，每个进程只初始化一次。
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


@lru_cache(maxsize=1)
def get_chroma_client():
    # PersistentClient 会把向量写入磁盘目录，容器通过 volume 保留这些数据。
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


def get_chroma_collection(collection_name):
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=collection_name,
        # 归一化向量配合 cosine 距离，便于把距离换算成直观相似度。
        metadata={"hnsw:space": "cosine"},
    )


@lru_cache(maxsize=10)
def build_embeddings(chunk_texts):
    # 对相同文本块复用计算结果，减少重复索引时的 CPU 开销。
    model = load_embedding_model()
    return model.encode(
        list(chunk_texts),
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()


def index_chunks_in_chroma(collection_name, chunks):
    collection = get_chroma_collection(collection_name)

    if collection.count() == len(chunks):
        return collection

    if collection.count() > 0:
        existing = collection.get()
        if existing.get("ids"):
            collection.delete(ids=existing["ids"])

    chunk_texts = tuple(chunk["text"] for chunk in chunks)
    embeddings = build_embeddings(chunk_texts)

    collection.add(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["text"] for chunk in chunks],
        metadatas=[chunk["metadata"] for chunk in chunks],
        embeddings=embeddings,
    )

    return collection


def retrieve_relevant_chunks(collection, question, top_k=TOP_K):
    # 用户问题和文档文本使用同一个模型编码，才能在同一向量空间比较。
    model = load_embedding_model()
    question_embedding = model.encode(
        [question],
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()[0]

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    relevant_chunks = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for document, metadata, distance in zip(documents, metadatas, distances):
        # Chroma 返回 cosine distance，这里转换为“越大越相关”的相似度。
        score = round(1 - float(distance), 3)
        if score >= SIMILARITY_THRESHOLD:
            relevant_chunks.append(
                {
                    "text": document,
                    "metadata": metadata,
                    "score": score,
                }
            )

    return relevant_chunks
