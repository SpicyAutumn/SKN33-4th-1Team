"""Web recommendations based on explicit catalog evidence, without external search."""
import re
from collections import Counter

GENERAL_KEYWORDS = {"미상", "불명", "조선", "고려", "삼국시대", "대한민국", "한국", "역사", "문화", "왕실"}


def key(value):
    # Parentheses contain alternative spellings, not an additional keyword.
    return re.sub(r"[\s_]", "", re.sub(r"\([^)]*\)", "", value)).casefold()


class Recommendations:
    def __init__(self, catalog):
        self.catalog = catalog
        self.keywords = {e.document_id: {key(k): k for k in e.keywords if len(key(k)) >= 2}
                         for e in catalog.entries}
        self.frequency = Counter(k for words in self.keywords.values() for k in words)
        self.titles = Counter(key(e.title) for e in catalog.entries)

    def build(self, document_id, limit=5):
        root = self.catalog.find(document_id)
        if root is None:
            return None
        title = key(root.title)
        words = self.keywords[root.document_id]
        groups = {"자료에 이름이 언급된 항목": [], "공통 주제어가 있는 항목": []}
        ambiguous = self.titles[title] > 1
        for entry in self.catalog.entries:
            if entry.document_id == root.document_id or key(entry.title) == title:
                continue
            other = self.keywords[entry.document_id]
            shared = sorted((w for w in words.keys() & other.keys()
                             if w not in GENERAL_KEYWORDS
                             and self.frequency[w] <= max(3, len(self.catalog.entries) * .01)),
                            key=lambda w: (self.frequency[w], w))
            evidence = []
            # Whole whitespace-delimited name avoids 청자 -> 청자부 substring matches.
            in_title = len(title) >= 2 and any(key(t) == title for t in entry.title.split())
            named = len(title) >= 2 and (title in other or in_title)
            reverse = len(key(entry.title)) >= 2 and key(entry.title) in words
            if named:
                evidence.append(f"{'제목' if in_title else '주제어'}에 ‘{root.title}’ 표기")
            if reverse:
                evidence.append(f"‘{root.title}’의 주제어에 이 항목 표기")
            if shared:
                evidence.append("공통 주제어: " + ", ".join(words[w] for w in shared[:3]))
            if not (named or reverse or len(shared) >= 2):
                continue
            group = "자료에 이름이 언급된 항목" if named or reverse else "공통 주제어가 있는 항목"
            score = (int(in_title) + int(named or reverse), len(shared), sum(1 / self.frequency[w] for w in shared))
            node = {"document_id": entry.document_id, "title": entry.title,
                    "reason": " · ".join(evidence), "item_type": entry.item_type,
                    "field": entry.field, "period": entry.period, "source_url": entry.source_url}
            groups[group].append((score, node))
        branches = []
        for label, candidates in groups.items():
            candidates.sort(key=lambda pair: (tuple(-v for v in pair[0]), pair[1]["title"], pair[1]["document_id"]))
            nodes = [node for _, node in candidates[:limit]]
            if nodes:
                branches.append({"title": label, "note": "목록의 표기상 연결이며, 실제 관계는 원문에서 확인해 주세요."
                                 + (" 같은 이름의 다른 인물·자료가 포함될 수 있어요." if ambiguous else ""), "nodes": nodes})
        return {"root": {"document_id": root.document_id, "title": root.title,
                         "fields": root.summary_fields(), "source_url": root.source_url}, "branches": branches}
