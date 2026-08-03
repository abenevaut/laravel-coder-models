"""Generate Q&A items from sections module."""


def _make_qa(doc_name: str, section: dict) -> dict:
    """Generate a Q&A item from a documentation section."""
    topic = doc_name.replace(".md", "").replace("-", " ")
    question = f"Explain {topic}: {section['title']}"
    return {
        "instruction": question,
        "input": "",
        "output": section["body"],
        "topic": topic,
    }


def build_knowledge_digest(sections_by_doc: dict) -> str:
    """Build a knowledge digest markdown from processed sections."""
    lines = [
        "# Laravel Expert Knowledge Base (official docs)\n",
        "Comprehensive Laravel documentation processed for training.\n",
    ]

    for doc_name, sections in sorted(sections_by_doc.items()):
        topic = doc_name.replace(".md", "")
        lines.append(f"\n## {topic.upper()}")
        for sec in sections[:3]:
            summary = sec["body"][:350].replace("\n", " ")
            lines.append(f"- **{sec['title']}**: {summary}")

    return "\n".join(lines)


def generate_qa(data: dict, **kwargs) -> dict:
    """Pipeline step: Generate Q&A items from sections.
    
    Input:  data["doc_name"] - document name
            data["sections"] - list of section dicts
    Output: data["qa_items"] - list of Q&A dicts
    """
    doc_name = data["doc_name"]
    qa_items = []
    for sec in data.get("sections", [])[:6]:
        qa_items.append(_make_qa(doc_name, sec))
    data["qa_items"] = qa_items
    return data
