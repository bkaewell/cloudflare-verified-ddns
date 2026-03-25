# ─── Standard library imports ───
import sys
import logging


# ─── Format configuration constants ───
LOG_LEVEL_EMOJIS = {
    logging.DEBUG: "🧱",
    logging.INFO: "🟢",
    logging.WARNING: "⚠️ ",
    logging.ERROR: "❌",
    logging.CRITICAL: "🔥",
}

LEVEL_NAME_MAP = {
    "WARNING": "WARN",
    "CRITICAL": "FATAL",
}

# ─── Formatters ───
class StatusFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        """
        Formatter that adds elapsed time, prepends an emoji per
        log level, and shortens selected level names.
        """
        record.elapsed_s = record.relativeCreated / 1000.0
        record.levelemoji = LOG_LEVEL_EMOJIS.get(record.levelno, "")
        record.levelname = LEVEL_NAME_MAP.get(record.levelname, record.levelname)
        return super().format(record)
        
# ─── Public logging setup API ───
def setup_logging(level=logging.INFO) -> None:
    """
    Configure global logging with emoji decorations and elapsed time.
    """
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    formatter = StatusFormatter(
        fmt="%(asctime)s  T+%(elapsed_s).0fs  %(levelemoji)s %(message)s", 
        datefmt="%Y-%m-%d %H:%M:%S", 
    )
    handler.setFormatter(formatter)

    root.addHandler(handler)

def get_logger(name: str) -> logging.Logger:
    """
    Return a namespaced logger for any module.
    """
    return logging.getLogger(f"{name}")
