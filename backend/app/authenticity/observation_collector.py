
import re

from app.authenticity.field_aliases import FIELD_ALIASES
from app.authenticity.generic_extractor import is_label_line
from app.authenticity.spatial_matching import match_spatial_value
from app.authenticity.field_validator import FIELD_VALIDATORS


# Prefer complete labels ("total tax") over shorter labels ("total"). Compile
# once; the patterns contain field vocabulary, never document-specific values.
def _compile_label_patterns():
    alias_fields = {}
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            alias_fields.setdefault(alias, set()).add(field)
    return [
        (fields, re.compile(
            r"^\s*" + re.escape(alias)
            + r"(?=\s|[:.#-]|$)\s*(?P<separator>[:.#-]?)\s*(?P<value>.*?)\s*$",
            re.IGNORECASE,
        ))
        for alias, fields in sorted(alias_fields.items(), key=lambda item: len(item[0]), reverse=True)
    ]


_LABEL_PATTERNS = _compile_label_patterns()


def normalize_observation(value):
    if value is None:
        return ""

    value = str(value).strip().lower()
    value = re.sub(r"\s+", " ", value)

    return value.strip(" .,:;-")


def _labelled_observation(index, lines):
    """Collect actual labelled values, including ones contradicting extraction."""
    line = lines[index]
    for fields, pattern in _LABEL_PATTERNS:
        match = pattern.match(line.get("text", ""))
        if not match:
            continue
        value = match.group("value").strip()
        source = line
        validators = [FIELD_VALIDATORS[field] for field in fields if field in FIELD_VALIDATORS]
        if value and not match.group("separator") and validators:
            # A title such as "TAX INVOICE" is not a tax amount. Keep invalid
            # values with explicit separators so genuine contradictions remain.
            if all(validator(value)[0] == "failed" for validator in validators):
                return fields, "", source
        if not value:
            spatial = match_spatial_value(line, lines)
            if spatial["status"] == "matched":
                source = spatial["candidate"]
                value = source.get("text", "").strip()
            elif spatial["status"] == "no_match" and index + 1 < len(lines):
                following = lines[index + 1]
                if (line.get("box") is None and following.get("box") is None
                        and line.get("page") == following.get("page")):
                    source = following
                    value = source.get("text", "").strip()
        if value and is_label_line(value):
            value = ""
        return fields, value, source
    return None


def collect_repeated_observations(lines, extracted_fields):

    observations = {}
    labelled = [_labelled_observation(index, lines) for index in range(len(lines))]

    for field_name, extracted in extracted_fields.items():

        if not isinstance(extracted, dict):
            continue

        expected_value = normalize_observation(
            extracted.get("value")
        )

        if not expected_value:
            continue

        matched = []

        for index, line in enumerate(lines):

            text = line.get("text", "").strip()

            if not text:
                continue

            source = line
            if labelled[index] is not None:
                field_names, matched_value, source = labelled[index]
                if field_name not in field_names or not matched_value:
                    continue
            else:
                # Unlabelled repeats are usable only when the value occurs as
                # a whole token; INV-12 must not match a different ID INV-123.
                match = re.search(
                    r"(?<!\w)" + re.escape(expected_value) + r"(?!\w)",
                    normalize_observation(text),
                )
                matched_value = match.group(0) if match else None

            if matched_value is None:
                continue

            matched.append({
                "value": matched_value,
                "confidence": source.get("confidence"),
                "page": source.get("page"),
                "box": source.get("box"),
                "source_text": source.get("text", ""),
            })

        # Remove duplicate observations at the same OCR position.
        unique = []
        seen = set()

        for item in matched:

            key = (
                normalize_observation(item["value"]),
                item["page"],
                str(item["box"])
            )

            if key not in seen:
                seen.add(key)
                unique.append(item)

        if len(unique) >= 2:
            observations[field_name] = unique

    return {
        "repeated_observations": observations,
        "observation_count": {
            field: len(values)
            for field, values in observations.items()
        }
    }
