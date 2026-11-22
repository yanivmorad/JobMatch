# src/scraper_service/utils.py
import re


def is_content_valid(text: str) -> bool:
    """
    Validates that scraped content is not an error page or blocked content.

    Args:
        text: The scraped text to validate

    Returns:
        True if content appears valid, False otherwise
    """
    if not text or len(text) < 150:
        return False
    invalid_markers = [
        "access denied",
        "robot check",
        "captcha",
        "404 not found",
        # דפי הגנה מבוטים (Cloudflare ודומיו) - נראים כמו תוכן אבל אין בהם משרה
        "performing security verification",
        "verify you are human",
        "checking your browser",
        "enable javascript and cookies to continue",
    ]
    lowered = text.lower()
    if any(marker in lowered for marker in invalid_markers):
        return False
    # "Just a moment..." של Cloudflare - רק כשהעמוד קצר (כדי לא לפסול משרה אמיתית)
    if "just a moment" in lowered and len(text.split()) < 150:
        return False
    return True


def clean_text(text: str) -> str:
    """
    Cleans scraped text by removing URLs, images, and excessive newlines.
    DO NOT MODIFY - This regex logic works perfectly.

    Args:
        text: The raw scraped text

    Returns:
        Cleaned text
    """
    if not text:
        return ""
    # Remove top URL if present, images, and extra newlines
    text = re.sub(r"^>?\s*https?://[^\n]+\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
