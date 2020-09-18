import logging
from src.constants.package_wide_constants import logfile


def get_logger(logger_name):
    logger = logging.getLogger(logger_name)

    if logger.hasHandlers() is False:
        logger.setLevel(logging.DEBUG)

        c_handler = logging.StreamHandler()
        c_handler.setLevel(logging.INFO)
        c_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        c_handler.setFormatter(c_formatter)
        logger.addHandler(c_handler)

        f_handler = logging.FileHandler(logfile)
        f_handler.setLevel(logging.DEBUG)
        f_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        f_handler.setFormatter(f_formatter)
        logger.addHandler(f_handler)

    return logger
