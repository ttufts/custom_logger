import argparse
import json
import logging
import os
import re
from pprint import pprint

class BreachSearcher:
    def __init__(self, breach_files, logger=None, verbose=False):
        self.verbose = verbose
        self.logger = logger
        self.breach_files = breach_files
        self.results = []

    def search_file_for_domain(self, filename, domain):
        results = []
        self.logger.debug("Searching {} for {}".format(filename, domain))
        #TODO: switch to memory mapping files
        with open(filename) as f:
            for line in f:
                line = line.decode("ascii", "ignore")
                try:
                    if domain in line:
                        m = re.findall("([a-zA-Z0-9-+_.]*@{})".format(domain), line)
                        if len(m) > 0:
                            self.logger.debug("Found {}".format(len(m)))
                            results.extend(m)
                except UnicodeDecodeError as e:
                    print domain
                    print line
                    raise e

        self.logger.debug("Found {} results for {} in {}".format(len(results), domain, filename))
        return results

    def search_breach_for_domain(self, domain):
        results = []
        for filename in self.breach_files:
            results.extend(self.search_file_for_domain(filename, domain))

        return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("search_domain", help="Domain name to search breach for")
    parser.add_argument("breach_dump", help="Path to breach dump. Can be file or directory. Directory will be recursed")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Print verbose debug output")
    args = parser.parse_args()

    breach_files = []

    if os.path.isfile(args.breach_dump):
        breach_files.append(args.breach_dump)

    if os.path.isdir(args.breach_dump):
        for root, dirs, files in os.walk(args.breach_dump):
            for filename in files:
                fullpath = os.path.join(root, filename)
                breach_files.append(fullpath)

    bs = BreachSearcher(breach_files = breach_files, verbose=args.verbose)

    results = bs.search_breach_for_domain(args.search_domain)

    pprint(results)
