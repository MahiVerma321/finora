
from pathlib import Path
import hashlib
import pymupdf


BASE_DIR = Path("test_revisions")

FILES = [
    ("Original", BASE_DIR / "original.pdf"),
    ("Revision 1", BASE_DIR / "revision_1.pdf"),
    ("Revision 2", BASE_DIR / "revision_2.pdf"),
]


def calculate_hash(data):
    return hashlib.sha256(data).hexdigest()


def extract_object_inventory(file_path):
    doc = pymupdf.open(file_path)

    inventory = {}

    try:
        for xref in range(1, doc.xref_length()):
            try:
                object_data = doc.xref_object(
                    xref,
                    compressed=False
                )

                stream_data = doc.xref_stream(xref)

                combined_data = (
                    object_data.encode("utf-8")
                    + (stream_data or b"")
                )

                inventory[xref] = {
                    "hash": calculate_hash(combined_data),
                    "object": object_data[:300],
                    "has_stream": stream_data is not None,
                }

            except Exception as error:
                inventory[xref] = {
                    "hash": None,
                    "object": None,
                    "has_stream": False,
                    "error": str(error),
                }

        return inventory

    finally:
        doc.close()


def compare_inventories(old_inventory, new_inventory):

    old_xrefs = set(old_inventory)
    new_xrefs = set(new_inventory)

    added = sorted(new_xrefs - old_xrefs)
    removed = sorted(old_xrefs - new_xrefs)

    common = old_xrefs & new_xrefs

    changed = []

    for xref in sorted(common):
        old_hash = old_inventory[xref]["hash"]
        new_hash = new_inventory[xref]["hash"]

        if old_hash != new_hash:
            changed.append(xref)

    return {
        "added_objects": added,
        "removed_objects": removed,
        "changed_objects": changed,
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
    }


inventories = {}

for label, path in FILES:
    if not path.exists():
        print(f"Missing file: {path}")
        continue

    print(f"\nExtracting objects: {label}")

    inventories[label] = extract_object_inventory(path)

    print(
        f"Objects extracted: {len(inventories[label])}"
    )


comparisons = [
    ("Original", "Revision 1"),
    ("Revision 1", "Revision 2"),
]


for old_label, new_label in comparisons:

    if old_label not in inventories or new_label not in inventories:
        continue

    print("\n" + "=" * 55)
    print(f"COMPARISON: {old_label} -> {new_label}")
    print("=" * 55)

    result = compare_inventories(
        inventories[old_label],
        inventories[new_label]
    )

    print("Added objects:", result["added_count"])
    print("Removed objects:", result["removed_count"])
    print("Changed objects:", result["changed_count"])

    print("\nAdded xrefs:", result["added_objects"])
    print("Removed xrefs:", result["removed_objects"])
    print("Changed xrefs:", result["changed_objects"])
