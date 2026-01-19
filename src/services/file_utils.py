# src/services/file_utils.py
import logging
import os

logger = logging.getLogger("JobMatchServer")

CURRENT_FILE_PATH = os.path.abspath(__file__)
# עולה 3 רמות: file_utils.py -> services -> src -> root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(CURRENT_FILE_PATH)))

DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_FILE = os.path.join(BASE_DIR, "results.json")
RESUME_PATH = os.path.join(DATA_DIR, "resume.txt")
CONTEXT_PATH = os.path.join(DATA_DIR, "Personal Context.txt")


def read_text_file(path: str) -> str:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    logger.warning(f"⚠️ הקובץ בנתיב {path} ריק")
                return content
        except Exception as e:
            logger.error(f"❌ שגיאה בקריאת הקובץ {path}: {e}")
    else:
        logger.error(f"❌ הקובץ לא נמצא: {path}")
    return ""
