Setup a logger
=======================

Setup a logger using Python logging

    import argparse
    from custom_logger import CustomLogger

    class TestClass():
        def __init__(self, verbose=False):
            self.logger = CustomLogger(self.__class__.__name__, "logfilename.log", verbose=verbose).get_logger()

    if __name__ == '__main__':
        parser = argparse.ArgumentParser()
        parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Print verbose debug output")
        args = parser.parse_args()

        t = TestClass(verbose=args.verbose)

        t.logger.debug("This is debug")
        t.logger.info("This is info")
        t.logger.warning("This is warning")
        t.logger.error("This is error")
        t.logger.critical("This is critical")
