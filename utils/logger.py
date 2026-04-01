import logging


LOGGER_NAME = "codefix_env"


def configure_logging(level: str = "INFO") -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)

    if logger.handlers:
        return

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.propagate = False


def log(message: str) -> None:
    logging.getLogger(LOGGER_NAME).info(message)