import logging


class AnsiColorHandler(logging.StreamHandler):
    LEVEL_COLORS = {
        "CRITICAL": 31,
        "ERROR": 31,
        "WARNING": 31,
        "INFO": 32,
        "DEBUG": 33,
    }

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        return f"\033[{self.LEVEL_COLORS[record.levelname]}m{message}\033[0m"
