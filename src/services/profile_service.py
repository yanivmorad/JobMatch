import logging

from services.file_utils import CONTEXT_PATH, RESUME_PATH, read_text_file

logger = logging.getLogger("JobMatchServer")


def get_resume_content() -> str:
    return read_text_file(RESUME_PATH)


def update_resume_content(content: str):
    try:
        with open(RESUME_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"✅ Resume updated: {len(content)} characters")
    except Exception as e:
        logger.error(f"❌ Error updating resume: {e}")
        raise


def get_context_content() -> str:
    return read_text_file(CONTEXT_PATH)


def update_context_content(content: str):
    try:
        with open(CONTEXT_PATH, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"✅ Context updated: {len(content)} characters")
    except Exception as e:
        logger.error(f"❌ Error updating context: {e}")
        raise
