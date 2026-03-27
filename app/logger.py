# ─── Standard library imports ───
import sys
import logging
from datetime import datetime


# ─── Format configuration constants ───
LOG_LEVEL_EMOJIS = {
    logging.DEBUG: "🧱",
    logging.INFO: "🟢",
    logging.WARNING: "🟠",
    logging.ERROR: "🔴",
    logging.CRITICAL: "💣",
}

LEVEL_NAME_MAP = {
    "WARNING": "WARN",
    "CRITICAL": "FATAL",
}

# ─── Formatters ───
class StatusFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Last emitted YYYY-MM-DD HH key. Used to detect hour boundaries.
        self._last_hour_key: str | None = None


    def format(self, record: logging.LogRecord) -> str:
        """
        Enrich each record with derived display fields and add a blank
        line when the stream rolls into a new hour.
        """

        # Derived fields consumed by the formatter template.
        record.elapsed_s = record.relativeCreated / 1000.0
        record.levelemoji = LOG_LEVEL_EMOJIS.get(record.levelno, "")
        record.levelname = LEVEL_NAME_MAP.get(record.levelname, record.levelname)

        # Hour bucket for this record.
        current_hour_key = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H")

        # Add a visual break only on an actual hour transition.
        insert_hour_break = (
            self._last_hour_key is not None
            and current_hour_key != self._last_hour_key
        )
        self._last_hour_key = current_hour_key

        # Format the record, then prepend a newline if the hour changed.
        rendered = super().format(record)
        if insert_hour_break:
            return f"\n{rendered}"
        return rendered
        
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
