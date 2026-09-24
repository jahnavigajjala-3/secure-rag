import re

def clean_text(text: str) -> str:
    """
    Clean and normalize extracted text content.
    - Removes non-printable null/binary characters.
    - Normalizes multi-space gaps within lines.
    - Preserves paragraph structural breaks (double newlines).
    """
    if not text:
        return ""

    # Replace null bytes and non-printable control characters (except newline, tab, carriage return)
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    # Replace windows line endings
    cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')

    # Replace excessive horizontal whitespace (tabs, multiple spaces) with single space
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)

    # Normalize excessive vertical line breaks (more than 2 consecutive newlines to 2)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned.strip()
