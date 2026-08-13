import re


def normalize_transliteration(text):
    """Canonicalize common Greek/Latin transliteration spelling variants
    (e.g. "Athanasios" vs "Athanasius", "Dionysios" vs "Dionysius", "Cosmas"
    vs "Kosmas") to the same form, so name search can match across them.
    Not a general phonetic algorithm -- just the specific substitution
    patterns found in this corpus, where names harvested from Greek-tradition
    sources and names carried over from the older Slavic/abbamoses corpus
    ended up using different transliteration conventions for the same
    underlying name."""

    text = text.lower()
    text = re.sub(r'c(?!h)', 'k', text)
    text = re.sub(r'y', 'i', text)
    text = re.sub(r'os\b', 'us', text)
    return text
