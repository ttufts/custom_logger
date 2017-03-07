Setup a logger
=======================

Setup a logger using Python logging

    from custom_logger import CustomLogger
    logger = CustomLogger(self.__class__.__name__, "logfilename.log", verbose=True).get_logger()
