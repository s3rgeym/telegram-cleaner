import logging


class AnsiColorHandler(logging.StreamHandler):
    _COLOR_CODES = {
        "CRITICAL": 31,
        "ERROR": 31,
        "WARNING": 31,
        "INFO": 32,
        "DEBUG": 33,
    }

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        isatty = getattr(self.stream, "isatty", None)
        if isatty and isatty():
            color_code = self._COLOR_CODES[record.levelname]
            return f"\033[{color_code}m{message}\033[0m"
        return message
