"""Inspect text changes retained in the submitted PDF's own incremental history."""
from difflib import SequenceMatcher
import re

import pymupdf

from app.revision_detector import analyze_prev_chain


def inspect_retained_text_changes(file_path, document):
    chain = analyze_prev_chain(file_path)
    revisions = chain.get("revision_chain", [])
    if chain.get("is_linearized") or len(revisions) < 2 or chain.get("status") != "completed":
        return []
    previous_offset = revisions[1]["xref_offset"]
    data = file_path.read_bytes()
    # Locate the complete earlier revision that references the verified /Prev target.
    marker = re.search(
        rb"(?:\r|\n)startxref\s+" + str(previous_offset).encode() + rb"\s+%%EOF(?=\s|$)", data
    )
    if marker is None:
        return []
    findings = []
    with pymupdf.open(stream=data[:marker.end()], filetype="pdf") as previous:
        if previous.is_repaired:
            return []
        for page_number, page in enumerate(document, start=1):
            if page_number > len(previous):
                continue
            old_page = previous[page_number - 1]
            # Match the page object and geometry, avoiding guesses after page rearrangement.
            if page.xref != old_page.xref or page.mediabox != old_page.mediabox or page.cropbox != old_page.cropbox or page.rotation != old_page.rotation:
                continue
            old_words = old_page.get_text("words", sort=True)
            new_words = page.get_text("words", sort=True)
            matcher = SequenceMatcher(None, [w[4] for w in old_words], [w[4] for w in new_words], autojunk=False)
            for kind, a, b, c, d in matcher.get_opcodes():
                if kind == "equal":
                    continue
                # Current geometry locates insertions/replacements. Deleted words retain
                # their earlier positions on the same page object, explicitly labelled.
                words = new_words[c:d] if c < d else old_words[a:b]
                for word in words:
                    findings.append({
                        "page": page_number,
                        "finding": f"retained_revision_{kind}",
                        "severity": "review",
                        "evidence_type": "embedded_revision_text_difference",
                        "text_bbox": list(word[:4]),
                        "coordinate_space": "unrotated_page",
                        "location_source": "current_revision" if c < d else "earlier_revision",
                        "original_text": " ".join(w[4] for w in old_words[a:b]),
                        "replacement_text": " ".join(w[4] for w in new_words[c:d]) or None,
                        "interpretation": "Extractable text differs from the preceding revision retained inside this PDF. Earlier positions mark removed text. The change may be intentional and requires review.",
                    })
    return findings
