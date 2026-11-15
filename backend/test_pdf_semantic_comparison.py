
from pathlib import Path
import hashlib
import json
import re
import pymupdf
import difflib

BASE_DIR = Path("test_revisions")

FILES = [
    ("Original", BASE_DIR / "original.pdf"),
    ("Revision 1", BASE_DIR / "revision_1.pdf"),
    ("Revision 2", BASE_DIR / "revision_2.pdf"),
    ("Text Modification", BASE_DIR / "text_modified.pdf")
]


def make_hash(data):
    return hashlib.sha256(data).hexdigest()


def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_semantic_inventory(file_path):

    doc = pymupdf.open(file_path)

    inventory = {
        "page_count": len(doc),
        "pages": []
    }

    try:
        for page_number, page in enumerate(doc, start=1):

            page_data = {
                "page_number": page_number,
                "text": normalize_text(page.get_text()),
                "dimensions": [
                    round(page.rect.width, 2),
                    round(page.rect.height, 2)
                ],
                "annotations": [],
                "images": [],
                "links": []
            }

            # Extract annotations
            annotations = page.annots()

            if annotations:
                for annot in annotations:

                    annotation_data = {
                        "type": annot.type[1],
                        "content": annot.info.get("content", ""),
                        "rect": [
                            round(value, 2)
                            for value in annot.rect
                        ]
                    }

                    page_data["annotations"].append(
                        annotation_data
                    )

            # Extract image fingerprints
            for image in page.get_images(full=True):

                xref = image[0]

                try:
                    extracted = doc.extract_image(xref)

                    image_hash = make_hash(
                        extracted["image"]
                    )

                    page_data["images"].append(image_hash)

                except Exception:
                    continue

            # Extract hyperlinks
            for link in page.get_links():

                page_data["links"].append({
                    "kind": link.get("kind"),
                    "uri": link.get("uri"),
                    "page": link.get("page"),
                    "rect": [
                        round(value, 2)
                        for value in link["from"]
                    ] if link.get("from") else None
                })

            inventory["pages"].append(page_data)

        return inventory

    finally:
        doc.close()

def get_text_difference(old_text, new_text):

    old_words = old_text.split()
    new_words = new_text.split()

    matcher = difflib.SequenceMatcher(
        None,
        old_words,
        new_words
    )

    changes = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag == "equal":
            continue

        changes.append({
            "change_type": tag,
            "previous_text": " ".join(old_words[i1:i2]),
            "current_text": " ".join(new_words[j1:j2])
        })

    return changes

def compare_semantics(old, new):

    results = {
        "text_changes": [],
        "annotation_changes": [],
        "image_changes": [],
        "link_changes": [],
        "page_dimension_changes": []
    }

    if old["page_count"] != new["page_count"]:
        results["page_count_changed"] = {
            "old": old["page_count"],
            "new": new["page_count"]
        }

    for index, (old_page, new_page) in enumerate(
        zip(old["pages"], new["pages"]),
        start=1
    ):

        if old_page["text"] != new_page["text"]:
            differences = get_text_difference(
                old_page["text"],
                new_page["text"]
            )

            results["text_changes"].append({
                "page": index,
                "differences": differences
            })

        if old_page["annotations"] != new_page["annotations"]:
            results["annotation_changes"].append({
                "page": index,
                "old": old_page["annotations"],
                "new": new_page["annotations"]
            })

        if sorted(old_page["images"]) != sorted(new_page["images"]):
            results["image_changes"].append(index)

        if old_page["links"] != new_page["links"]:
            results["link_changes"].append(index)

        if old_page["dimensions"] != new_page["dimensions"]:
            results["page_dimension_changes"].append(index)

    return results


inventories = {}

for label, path in FILES:

    if not path.exists():
        print(f"Missing file: {path}")
        continue

    print(f"\nAnalyzing: {label}")

    inventories[label] = extract_semantic_inventory(path)


comparisons = [
    ("Original", "Revision 1"),
    ("Revision 1", "Revision 2"),
    ("Original", "Text Modification")
]


for old_label, new_label in comparisons:

    if old_label not in inventories or new_label not in inventories:
        continue

    print("\n" + "=" * 55)
    print(f"{old_label} -> {new_label}")
    print("=" * 55)

    result = compare_semantics(
        inventories[old_label],
        inventories[new_label]
    )

    print(
        json.dumps(result, indent=4, ensure_ascii=False)
    )
