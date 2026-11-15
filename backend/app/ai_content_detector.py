
import re
import statistics
from collections import Counter

def clean_text(text):
    """Normalize text before linguistic analysis."""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def remove_structured_fields(text):
    """Remove ticket identifiers, dates, prices and common ticket labels."""

    patterns = [
        # Dates and times
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{1,2}:\d{2}(?:\s?[AP]M)?\b",

        # Prices
        r"\b(?:INR|Rs\.?|₹)\s?[\d,]+(?:\.\d{1,2})?\b",

        # Booking identifiers
        r"\b[A-Z0-9]{6,}\b",
        r"\b\d{10,}\b",
        r"\b(?:PNR|Booking ID|Ticket No|Invoice No)\s*[:#-]?\s*[A-Z0-9-]+\b",

        # Common ticket labels
        r"\b(?:passenger|boarding point|dropping point)\b",
        r"\b(?:journey date|travel date|departure time|arrival time)\b",
        r"\b(?:seat number|seat no|booking status|ticket status)\b",
        r"\b(?:bus type|bus operator|service provider)\b",
        r"\b(?:source|destination|origin|departure|arrival)\b",
    ]

    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", text).strip()

def analyze_repeated_phrases(text):
    """Find meaningful repeated two- and three-word phrases."""

    stopwords = {
        "the", "is", "are", "was", "were", "has",
        "have", "had", "been", "being", "your",
        "you", "our", "and", "or", "of", "to",
        "in", "on", "at", "for", "with", "by",
        "a", "an", "please", "this", "that"
    }

    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

    phrases = []

    for size in (2, 3):
        for i in range(len(words) - size + 1):
            phrase_words = words[i:i + size]

            if any(word in stopwords for word in phrase_words):
                continue

            phrase = " ".join(phrase_words)
            phrases.append(phrase)

    counts = Counter(phrases)

    return [
        {
            "phrase": phrase,
            "count": count
        }
        for phrase, count in counts.items()
        if count >= 2
    ][:10]

def split_sentences(text):
    """Split text into sentence-like units."""

    return [
        sentence.strip()
        for sentence in re.split(r"[.!?]+", text)
        if sentence.strip()
    ]



def analyze_repetition(text):
    """Identify meaningful repeated words after removing stopwords."""

    stopwords = {
        "the", "is", "are", "was", "were", "has",
        "have", "had", "been", "being", "your",
        "you", "our", "and", "or", "of", "to",
        "in", "on", "at", "for", "with", "by",
        "a", "an", "this", "that", "not", "from",
        "can", "will", "please", "their", "they",
        "them", "it", "its", "as", "be", "but",
        "if", "all", "any", "only", "now"
    }

    words = [
        word for word in re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        if word not in stopwords
    ]

    if not words:
        return {
            "repeated_words": [],
            "repetition_ratio": 0
        }

    counts = Counter(words)

    repeated = [
        {"word": word, "count": count}
        for word, count in counts.items()
        if count >= 3
    ]

    repetition_ratio = (
        sum(count - 1 for count in counts.values() if count >= 2)
        / len(words)
    )

    return {
        "repeated_words": repeated,
        "repetition_ratio": round(repetition_ratio, 3)
    }

def analyze_sentence_lengths(text):
    """Analyze variation in sentence lengths."""

    sentences = split_sentences(text)

    lengths = [
        len(sentence.split())
        for sentence in sentences
    ]

    if len(lengths) < 2:
        return {
            "sentence_count": len(lengths),
            "average_sentence_length": (
                round(statistics.mean(lengths), 2)
                if lengths else 0
            ),
            "sentence_length_variation": None
        }

    return {
        "sentence_count": len(lengths),
        "average_sentence_length": round(
            statistics.mean(lengths), 2
        ),
        "sentence_length_variation": round(
            statistics.pstdev(lengths), 2
        )
    }


def analyze_vocabulary(text):
    """Measure vocabulary diversity."""

    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

    if not words:
        return {
            "word_count": 0,
            "unique_word_count": 0,
            "vocabulary_diversity": 0
        }

    unique_words = set(words)

    return {
        "word_count": len(words),
        "unique_word_count": len(unique_words),
        "vocabulary_diversity": round(
            len(unique_words) / len(words), 3
        )
    }

def analyze_ai_content(text):
    """Run traditional linguistic pattern analysis."""

    original_text = clean_text(text)

    # Remove structured ticket information
    filtered_text = remove_structured_fields(original_text)

    if len(filtered_text.split()) < 30:
        return {
            "status": "insufficient_text",
            "message": (
                "At least 30 meaningful words are required "
                "after removing structured fields."
            )
        }

    repetition = analyze_repetition(filtered_text)

    sentence_analysis = analyze_sentence_lengths(
        filtered_text
    )

    vocabulary = analyze_vocabulary(filtered_text)

    repeated_phrases = analyze_repeated_phrases(
        filtered_text
    )

    return {
        "status": "completed",
        "analysis_type": "traditional_linguistic_analysis",
        "checks": {
            "repetition": repetition,
            "repeated_phrases": repeated_phrases,
            "sentence_structure": sentence_analysis,
            "vocabulary": vocabulary
        },
        "assessment": (
            "Linguistic patterns analyzed after filtering "
            "structured document fields. These indicators "
            "cannot establish AI authorship."
        )
    }
