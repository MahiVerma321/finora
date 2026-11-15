
from pathlib import Path
import re

def detect_linearization(pdf_data: bytes):
    """
    Detect whether a PDF contains a linearization dictionary.
    It is normally located near the beginning of the file.
    """
    header = pdf_data[:1024]

    return bool(
        re.search(rb"/Linearized\s+[\d.]+", header)
    )

def inspect_revision_markers(file_path: Path):
    """
    Detect possible incremental PDF updates by inspecting
    startxref and %%EOF markers.

    This is a structural screening technique, not proof
    that a PDF has been manipulated.
    """

    with open(file_path, "rb") as file:
        pdf_data = file.read()

    is_linearized = detect_linearization(pdf_data)
    
    # Support LF, CRLF, and CR line endings.

    startxref_pattern = re.compile(
        rb"(?<![^\r\n])[ \t]*startxref[ \t]*"
        rb"[\r\n]+[ \t]*(\d+)[ \t]*(?=[\r\n]|$)"
    )

    eof_pattern = re.compile(
        rb"(?<![^\r\n])[ \t]*%%EOF[ \t]*(?=[\r\n]|$)"
    )


    startxref_matches = list(startxref_pattern.finditer(pdf_data))
    eof_matches = list(eof_pattern.finditer(pdf_data))

    valid_offsets = []
    invalid_offsets = []

    for match in startxref_matches:
        offset = int(match.group(1))

        # Linearized PDFs may contain startxref 0
        # as part of their special file structure.
        if is_linearized and offset == 0:
            continue

        if offset < 0 or offset >= len(pdf_data):
            invalid_offsets.append(offset)
            continue

        target = pdf_data[offset:offset + 200].lstrip()

        if (
            target.startswith(b"xref")
            or re.match(rb"\d+\s+\d+\s+obj\b", target)
        ):
            valid_offsets.append(offset)
        else:
            invalid_offsets.append(offset)

    revision_count = len(valid_offsets)

    revision_count = len(valid_offsets)

    if is_linearized:
        status = "linearized_structure_detected"
        interpretation = (
            "The PDF is linearized. Multiple cross-reference "
            "sections and startxref markers may be part of its "
            "linearization structure. Incremental revision "
            "count cannot be reliably determined using "
            "marker counting alone."
        )

    elif revision_count > 1:
        status = "possible_incremental_updates"
        interpretation = (
            "Multiple valid startxref markers were found. "
            "This may indicate incremental PDF updates."
        )

    elif revision_count == 1:
        status = "single_revision_detected"
        interpretation = (
            "One valid startxref marker was found. "
            "No additional incremental revision was detected."
        )

    else:
        status = "inconclusive"
        interpretation = (
            "No valid startxref marker was identified."
        )

    return {
        "technique": "PDF Incremental Revision Analysis",
        "startxref_marker_count": len(startxref_matches),
        "eof_marker_count": len(eof_matches),
        "valid_startxref_offsets": valid_offsets,
        "invalid_startxref_offsets": invalid_offsets,
        "status": status,
        "interpretation": interpretation,
        "is_linearized": is_linearized,
        "possible_revision_count": (
            None if is_linearized else max(0, revision_count - 1)
        ),
        "warning": (
            "Revision markers are structural indicators only. "
            "They do not establish whether a document was forged "
            "or whether a particular revision changed its content."
        )
    }


import re


def extract_dictionary(data: bytes, start: int):
    """
    Extract a PDF dictionary beginning at '<<' while
    respecting nested dictionaries and literal strings.
    """

    if data[start:start + 2] != b"<<":
        return None

    depth = 0
    in_string = False
    escaped = False
    i = start

    while i < len(data):
        char = data[i:i + 1]

        if in_string:
            if escaped:
                escaped = False
            elif char == b"\\":
                escaped = True
            elif char == b"(":
                # Nested parentheses inside PDF strings
                pass
            elif char == b")":
                in_string = False

        else:
            if char == b"(":
                in_string = True
            elif data[i:i + 2] == b"<<":
                depth += 1
                i += 1
            elif data[i:i + 2] == b">>":
                depth -= 1
                i += 1

                if depth == 0:
                    return data[start:i + 1]

        i += 1

    return None


def get_xref_dictionary(pdf_data: bytes, offset: int):
    """
    Locate the dictionary belonging to a cross-reference
    table or cross-reference stream.
    """

    if offset < 0 or offset >= len(pdf_data):
        return None, "invalid_offset"

    remaining = pdf_data[offset:].lstrip()

    # Classic cross-reference table
    if remaining.startswith(b"xref"):
        trailer_match = re.search(
            rb"\btrailer\b",
            remaining
        )

        if not trailer_match:
            return None, "missing_trailer"

        dictionary_start = (
            trailer_match.end()
            + len(remaining[trailer_match.end():])
            - len(remaining[trailer_match.end():].lstrip())
        )

        dictionary = extract_dictionary(
            remaining,
            dictionary_start
        )

        if dictionary:
            return dictionary, "classic_xref"

        return None, "invalid_trailer_dictionary"

    # Cross-reference stream
    if re.match(rb"\d+\s+\d+\s+obj\b", remaining):
        dictionary_start = remaining.find(b"<<")

        if dictionary_start == -1:
            return None, "missing_xref_stream_dictionary"

        dictionary = extract_dictionary(
            remaining,
            dictionary_start
        )

        if dictionary and re.search(
            rb"/Type\s*/XRef\b",
            dictionary
        ):
            return dictionary, "xref_stream"

        return None, "not_an_xref_stream"

    return None, "unknown_xref_structure"


def extract_prev_offset(dictionary: bytes):
    """
    Extract the direct integer value of /Prev.
    """

    if not dictionary:
        return None

    match = re.search(
        rb"/Prev\s+(\d+)\b",
        dictionary
    )

    if match:
        return int(match.group(1))

    return None


def analyze_prev_chain(file_path: Path):
    """
    Follow the /Prev references from the latest PDF
    cross-reference section backwards.
    """

    with open(file_path, "rb") as file:
        pdf_data = file.read()

    is_linearized = detect_linearization(pdf_data)
    
    marker_pattern = re.compile(
        rb"(?<![^\r\n])[ \t]*startxref[ \t]*"
        rb"[\r\n]+[ \t]*(\d+)[ \t]*(?=[\r\n]|$)"
    )

    matches = list(marker_pattern.finditer(pdf_data))

    if not matches:
        return {
            "technique": "PDF Previous Revision Chain Analysis",
            "status": "inconclusive",
            "message": "No startxref marker was found.",
            "revision_chain": []
        }

    current_offset = int(matches[-1].group(1))

    revision_chain = []
    visited = set()
    status = "completed"

    while True:

        if current_offset in visited:
            status = "cycle_detected"
            break

        if current_offset < 0 or current_offset >= len(pdf_data):
            status = "invalid_offset"
            break

        visited.add(current_offset)

        dictionary, xref_type = get_xref_dictionary(
            pdf_data,
            current_offset
        )

        if dictionary is None:
            status = "invalid_xref_structure"
            break

        previous_offset = extract_prev_offset(dictionary)

        revision_chain.append({
            "xref_offset": current_offset,
            "xref_type": xref_type,
            "previous_offset": previous_offset
        })

        if previous_offset is None:
            break

        if previous_offset in visited:
            status = "cycle_detected"
            break

        if previous_offset < 0 or previous_offset >= len(pdf_data):
            status = "invalid_offset"
            break

        current_offset = previous_offset

    xref_section_count = len(revision_chain)

    if status == "completed":

        if is_linearized:
            interpretation = (
                "The PDF is linearized. Multiple cross-reference "
                "sections may belong to its linearization structure. "
                "They cannot independently establish incremental "
                "revisions."
            )

        elif xref_section_count > 1:
            interpretation = (
                "Multiple cross-reference sections are connected "
                "through /Prev references. Incremental updates "
                "are structurally indicated, but their content "
                "and purpose are not established."
            )

        else:
            interpretation = (
                "One cross-reference section was found. "
                "No previous revision was referenced."
            )
    else:
        interpretation = (
            "The previous revision chain could not be followed "
            "completely. Inspect the reported structural issue."
        )

    return {
        "technique": "PDF Previous Revision Chain Analysis",
        "status": (
            "linearized_structure_detected"
            if is_linearized and status == "completed"
            else status
        ),
        "is_linearized": is_linearized,
        "xref_section_count": xref_section_count,
        "incremental_revision_count": (
            None
            if is_linearized
            else max(0, xref_section_count - 1)
        ),
        "revision_chain": revision_chain,
        "interpretation": interpretation,
        "warning": (
            "Cross-reference structures are not proof of "
            "manipulation. Linearization and legitimate PDF "
            "operations can produce multiple sections."
        )
    }
