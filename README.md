Setup a logger
=======================

Setup a logger using Python logging

    from custom_logger import CustomLogger

    class TestClass():
        def __init__(self, verbose=False):
            logger = CustomLogger(self.__class__.__name__, "logfilename.log", verbose=verbose).get_logger()
