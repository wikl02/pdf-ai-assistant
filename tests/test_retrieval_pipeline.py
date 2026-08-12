from document_loader import extract_text_units
from text_splitter import split_units_to_chunks
import vector_store


def test_txt_parser_preserves_natural_rule_lines():
    content = (
        "产品FAQ\n"
        "用户购买产品后 7 个自然日内可以申请退款。\n"
        "退款申请审核通过后，款项将在 5 个工作日内退回。\n"
    ).encode("utf-8")

    units = extract_text_units("产品FAQ.txt", content, "txt")

    assert [unit["start_line"] for unit in units] == [1, 2, 3]
    assert units[1]["text"] == "用户购买产品后 7 个自然日内可以申请退款。"


def test_splitter_prefers_sentence_boundaries_for_long_content():
    units = [
        {
            "source_name": "制度.txt",
            "file_type": "txt",
            "location_type": "line",
            "page": 0,
            "start_line": 1,
            "end_line": 1,
            "text": "第一条规则说明。第二条规则说明。第三条规则说明。",
        }
    ]

    chunks = split_units_to_chunks(units, chunk_size=15, overlap=3)

    assert len(chunks) >= 2
    assert chunks[0]["text"].endswith("。")
    assert all(chunk["text"] for chunk in chunks)


class _FakeEmbeddingModel:
    def encode(self, texts, **_kwargs):
        return _EncodedVectors([[1.0, 0.0] for _text in texts])


class _EncodedVectors(list):
    def tolist(self):
        return list(self)


class _FakeCollection:
    def __init__(self):
        self.items = [
            {
                "id": "price",
                "text": "旗舰版价格为每年 29999 元。",
                "metadata": {"source_name": "产品FAQ.txt", "chunk_id": 1},
                "distance": 0.35,
            },
            {
                "id": "refund",
                "text": "用户购买产品后 7 个自然日内可以申请退款。",
                "metadata": {"source_name": "产品FAQ.txt", "chunk_id": 2},
                "distance": 0.70,
            },
        ]

    def count(self):
        return len(self.items)

    def query(self, **_kwargs):
        ordered = sorted(self.items, key=lambda item: item["distance"])
        return {
            "ids": [[item["id"] for item in ordered]],
            "documents": [[item["text"] for item in ordered]],
            "metadatas": [[item["metadata"] for item in ordered]],
            "distances": [[item["distance"] for item in ordered]],
        }

    def get(self, where_document, **_kwargs):
        token = where_document["$contains"]
        matched = [item for item in self.items if token in item["text"]]
        return {
            "ids": [item["id"] for item in matched],
            "documents": [item["text"] for item in matched],
            "metadatas": [item["metadata"] for item in matched],
        }


def test_hybrid_retrieval_recovers_exact_business_rule(monkeypatch):
    monkeypatch.setattr(vector_store, "load_embedding_model", lambda: _FakeEmbeddingModel())

    results = vector_store.retrieve_relevant_chunks(
        _FakeCollection(),
        "购买产品后多久还能退款？",
        top_k=2,
    )

    assert results
    assert "7 个自然日" in results[0]["text"]
    assert results[0]["score"] > results[1]["score"]
