import argparse
import json
import logging
import os
import re
from pprint import pprint

class BreachSearcher:
    def __init__(self, breach_data, logger=None, verbose=False):
        self.verbose = verbose
        self.setup_logger()

        self.breach_data = breach_data

    def setup_logger(self):
        self.logger = logging.getLogger()

        if len(self.logger.handlers) == 0:
            self.logger.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s | %(levelname)-8s| %(message)s')

            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            if self.verbose:
                ch.setLevel(logging.DEBUG)
            else:
                ch.setLevel(logging.INFO)
            self.logger.addHandler(ch)

    def get_domain_from_email(self, email):
        username, domain = email.split("@")

        return domain.strip().lower()

    def search_breach_for_domain(self, domain):
        results = []

        domain = domain.decode("ascii", "ignore")
        self.logger.debug("Searching for {}".format(domain))

        domain_email = "@{}".format(domain)
        subdomain = ".{}".format(domain)

        for site in self.breach_data:
            for email in self.breach_data[site]:
                try:
                    if domain_email in email:
                        results.append((email, site))
                        continue
                    if email.endswith("subdomain"):
                        results.append((email, site))
                        continue
                except UnicodeDecodeError:
                    print domain_email

        self.logger.debug("Found {} results for {}".format(len(results), domain))
        return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("breach_dump", help="Path to breach dump. Can be file or directory. Directory will be recursed")
    parser.add_argument("search_domain", help="Domain name to search breach for")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Print verbose debug output")
    args = parser.parse_args()

    if os.path.isfile(args.breach_dump):
        with open(args.breach_dump) as f:
            breach_data = json.load(f)

    bs = BreachSearcher(breach_data=breach_data, verbose=args.verbose)

    if os.path.isfile(args.search_domain):
        with open(args.search_domain) as f:
            for line in f:
                if "@" in line:
                    domain = bs.get_domain_from_email(line.strip())
                else:
                    domain = line.strip()
                results = bs.search_breach_for_domain(domain)
    else:
        results = bs.search_breach_for_domain(args.search_domain)

    pprint(results)
