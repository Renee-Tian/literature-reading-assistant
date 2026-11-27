import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
APP_LOG_FILE = LOG_DIR / "app.log"
AGENT_TRACE_FILE = LOG_DIR / "agent_traces.jsonl"


LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


def _has_file_handler(logger, file_path):
    target = Path(file_path).resolve()

    for handler in logger.handlers:
        if not isinstance(handler, logging.FileHandler):
            continue

        if Path(handler.baseFilename).resolve() == target:
            return True

    return False


def _build_file_handler(file_path, formatter):
    handler = RotatingFileHandler(
        file_path,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    return handler


def configure_logging(app=None):
    """配置 app.log 与 agent_traces.jsonl。"""

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not _has_file_handler(root_logger, APP_LOG_FILE):
        root_logger.addHandler(
            _build_file_handler(
                APP_LOG_FILE,
                logging.Formatter(LOG_FORMAT),
            )
        )

    if not any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        for handler in root_logger.handlers
    ):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter(LOG_FORMAT)
        )
        console_handler.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)

    trace_logger = logging.getLogger("agent_trace")
    trace_logger.setLevel(logging.INFO)
    trace_logger.propagate = False

    if not _has_file_handler(trace_logger, AGENT_TRACE_FILE):
        trace_logger.addHandler(
            _build_file_handler(
                AGENT_TRACE_FILE,
                logging.Formatter("%(message)s"),
            )
        )

    if app is not None:
        app.logger.setLevel(logging.INFO)

    return {
        "app_log": str(APP_LOG_FILE),
        "agent_trace": str(AGENT_TRACE_FILE),
    }
