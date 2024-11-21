import logging
from oufoaler.config import Config

config = Config()


class CustomFormatter(logging.Formatter):
    LEVEL_SHORT = {
        "DEBUG": "DEBUG",
        "INFO": "INFO ",
        "WARNING": "WARN ",
        "ERROR": "ERROR",
        "CRITICAL": "CRIT ",
    }

    def format(self, record):
        record.levelname = self.LEVEL_SHORT.get(record.levelname, record.levelname)
        return super().format(record)


def setup_logger():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger()

    # Set custom formatter
    handler = logger.handlers[0]
    handler.setFormatter(CustomFormatter("%(asctime)s - %(levelname)s - %(message)s"))

    # Set specific log levels
    logging.getLogger("requests").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.INFO)

    return logger
