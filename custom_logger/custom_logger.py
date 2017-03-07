import argparse
import logging


class CustomLogger:
    def __init__(self, class_name, log_file=None, verbose=False):
        self.verbose = verbose
        self.class_name = class_name[:24]
        self.log_file = log_file

        self.setup_logger()

        self.info = self.logger.info
        self.warning = self.logger.warning
        self.error = self.logger.error
        self.critical = self.logger.critical
        self.debug = self.logger.debug

    def get_logger(self):
        return self.logger

    def setup_logger(self):
        self.logger = logging.getLogger(self.class_name)

        if not hasattr(self.logger, "stream"):
            self.logger.stream = False

        if not hasattr(self.logger, "file"):
            self.logger.file = False

        if self.logger.stream and self.logger.file:
            return

        self.logger.setLevel(logging.DEBUG)
        self.log_format = '%(asctime)s | %(levelname)-8s| {0: <25} | %(message)s'.format(self.class_name)

        formatter = logging.Formatter(self.log_format)

        if not self.logger.stream:
            # Only print to the console if verbose is turned on
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)

            if self.verbose:
                ch.setLevel(logging.DEBUG)
            else:
                ch.setLevel(logging.CRITICAL)

            self.logger.addHandler(ch)
            self.logger.stream = True

        if not self.logger.file and self.log_file is not None:
            fh = logging.FileHandler(self.log_file)
            if self.verbose:
                fh.setLevel(logging.DEBUG)
            else:
                fh.setLevel(logging.INFO)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
            self.logger.file = True


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="Log file")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Print verbose debug output")
    args = parser.parse_args()

    cl = CustomLogger("Logger", log_file=args.file, verbose=args.verbose)

    logger = cl.get_logger()

    logger.debug("This is debug")
    logger.info("This is info")
    logger.warning("This is warning")
    logger.error("This is error")
    logger.critical("This is critical")
