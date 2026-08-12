from functools import lru_cache

# 本模块负责 Embedding 模型加载、Chroma 持久化及向量相似度检索。
import re
import chromadb
from sentence_transformers import SentenceTransformer

from config import (
    CHROMA_DB_PATH,
    EMBEDDING_MODEL_NAME,
    HYBRID_KEYWORD_WEIGHT,
    KEYWORD_QUERY_TOKEN_LIMIT,
    SIMILARITY_THRESHOLD,
    TOP_K,
    VECTOR_CANDIDATE_MULTIPLIER,
)


_QUESTION_STOP_PHRASES = {
    "什么",
    "多少",
    "多久",
    "如何",
    "怎么",
    "是否",
    "可以",
    "能否",
    "请问",
    "相关",
    "信息",
    "文档",
    "用户",
    "产品",
    "购买",
    "申请",
    "进行",
    "超过",
}


def keyword_query_tokens(question):
    """提取适合精确召回的中文短语、英文词和数字。"""

    normalized = re.sub(r"[\s\"'“”‘’？?！!，,。；;：:（）()]+", " ", question.lower()).strip()
    tokens = []

    for segment in normalized.split():
        if re.fullmatch(r"[a-z0-9_.+-]+", segment):
            tokens.append(segment)
            continue

        chinese = "".join(re.findall(r"[\u4e00-\u9fff]", segment))
        for phrase in _QUESTION_STOP_PHRASES:
            chinese = chinese.replace(phrase, "")

        if len(chinese) >= 2:
            # 完整业务短语优先，二元词负责召回“退款期限”和“多久退款”等近似问法。
            tokens.append(chinese)
            tokens.extend(chinese[index : index + 2] for index in range(len(chinese) - 1))

        tokens.extend(re.findall(r"\d+(?:\.\d+)?", segment))

    unique_tokens = []
    for token in sorted(tokens, key=len, reverse=True):
        if len(token) < 2 or token in unique_tokens:
            continue
        unique_tokens.append(token)
        if len(unique_tokens) >= KEYWORD_QUERY_TOKEN_LIMIT:
            break
    return unique_tokens


def _keyword_score(document, tokens):
    if not tokens:
        return 0.0
    normalized_document = document.lower()
    matched_tokens = [token for token in tokens if token in normalized_document]
    if not matched_tokens:
        return 0.0

    # 一个明确业务词（如“退款”）就应有足够召回权重；额外命中继续加分。
    longest_match = max(len(token) for token in matched_tokens)
    base_score = min(1.0, longest_match / 4)
    additional_score = min(0.4, max(0, len(matched_tokens) - 1) * 0.1)
    return min(1.0, base_score + additional_score)


def _keyword_candidates(collection, tokens):
    candidates = {}
    for token in tokens:
        results = collection.get(
            where_document={"$contains": token},
            include=["documents", "metadatas"],
        )
        for chunk_id, document, metadata in zip(
            results.get("ids", []),
            results.get("documents", []),
            results.get("metadatas", []),
        ):
            candidates[str(chunk_id)] = {
                "text": document,
                "metadata": metadata,
                "_vector_score": 0.0,
            }
    return candidates


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

    candidate_count = min(
        collection.count(),
        max(top_k, top_k * VECTOR_CANDIDATE_MULTIPLIER),
    )
    if candidate_count == 0:
        return []

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=candidate_count,
        include=["documents", "metadatas", "distances"],
    )

    candidates = {}
    result_ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for chunk_id, document, metadata, distance in zip(
        result_ids, documents, metadatas, distances
    ):
        candidates[str(chunk_id)] = {
            "text": document,
            "metadata": metadata,
            "_vector_score": max(0.0, min(1.0, 1 - float(distance))),
        }

    tokens = keyword_query_tokens(question)
    for chunk_id, candidate in _keyword_candidates(collection, tokens).items():
        candidates.setdefault(chunk_id, candidate)

    relevant_chunks = []
    for candidate in candidates.values():
        vector_score = candidate.pop("_vector_score")
        keyword_score = _keyword_score(candidate["text"], tokens)
        if tokens:
            score = (
                (1 - HYBRID_KEYWORD_WEIGHT) * vector_score
                + HYBRID_KEYWORD_WEIGHT * keyword_score
            )
        else:
            score = vector_score

        # 关键词命中可直接保留，向量候选则继续服从最低相关度阈值。
        if keyword_score >= 0.5 or score >= SIMILARITY_THRESHOLD:
            relevant_chunks.append({**candidate, "score": round(score, 3)})

    relevant_chunks.sort(key=lambda item: item["score"], reverse=True)
    return relevant_chunks[:top_k]
