from bisect import bisect_right

from config import CHUNK_OVERLAP, CHUNK_SIZE


def format_location(metadata):
    location_type = metadata.get("location_type")

    if location_type == "page_line":
        if metadata["start_line"] == metadata["end_line"]:
            return f"第 {metadata['page']} 页，第 {metadata['start_line']} 行"
        return f"第 {metadata['page']} 页，第 {metadata['start_line']}-{metadata['end_line']} 行"

    if location_type == "paragraph":
        return f"第 {metadata['start_line']} 段"

    if location_type == "row":
        return f"第 {metadata['start_line']} 行"

    if location_type == "sheet_row":
        return f"{metadata.get('sheet', '工作表')}，第 {metadata['start_line']} 行"

    if location_type == "line":
        return f"第 {metadata['start_line']}-{metadata['end_line']} 行"

    return "未知位置"


def split_units_to_chunks(units, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []

    for unit in units:
        text = unit["text"]
        if not text:
            continue

        line_offsets = []
        position = 0
        lines = text.splitlines() or [text]
        for line in lines:
            line_offsets.append(position)
            position += len(line) + 1

        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            raw_chunk_text = text[start:end]
            chunk_text = raw_chunk_text.strip()

            if chunk_text:
                leading_space = len(raw_chunk_text) - len(raw_chunk_text.lstrip())
                trailing_space = len(raw_chunk_text) - len(raw_chunk_text.rstrip())
                content_start = start + leading_space
                content_end = end - trailing_space

                start_line = unit["start_line"]
                end_line = unit["end_line"]
                if unit["location_type"] in {"page_line", "line"}:
                    start_line = unit["start_line"] + bisect_right(line_offsets, content_start) - 1
                    end_line = unit["start_line"] + bisect_right(line_offsets, content_end - 1) - 1

                metadata = {
                    "source_name": unit["source_name"],
                    "file_type": unit["file_type"],
                    "location_type": unit["location_type"],
                    "page": int(unit.get("page", 0)),
                    "start_line": int(start_line),
                    "end_line": int(end_line),
                    "sheet": unit.get("sheet", ""),
                    "chunk_id": len(chunks) + 1,
                }

                chunks.append(
                    {
                        "id": str(len(chunks) + 1),
                        "text": chunk_text,
                        "metadata": metadata,
                    }
                )

            if end == len(text):
                break

            start = end - overlap

    return chunks


def build_preview_text(chunks, limit=5000):
    sections = []
    current_length = 0

    for chunk in chunks:
        metadata = chunk["metadata"]
        location = format_location(metadata)
        section = (
            f"--- {metadata['source_name']} | {location} | 文本块 {metadata['chunk_id']} ---\n"
            f"{chunk['text']}"
        )
        if current_length + len(section) > limit:
            break
        sections.append(section)
        current_length += len(section)

    return "\n\n".join(sections)
