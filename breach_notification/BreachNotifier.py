import argparse
import json
import logging
import os
import zipfile
import time

from BreachSearcher import BreachSearcher

class BreachNotifier:
    def __init__(self, breach_name, breach_data, verbose=False):
        self.verbose = verbose
        self.setup_logger()

        self.breach_name = breach_name
        self.breach_data = breach_data

        self.breach_search = BreachSearcher(breach_data=self.breach_data,
                                            verbose=self.verbose)

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

    def search_breach_for_domain(self, domain):
        return self.breach_search.search_breach_for_domain(domain)

    def search_breach_for_domains(self, domains):
        results = {}
        for domain in domains:
            results[domain] = self.search_breach_for_domain(domain)

        return results

    def format_results(self, results):
        output = ""
        for email, site in results:
            output += u"{}: {}\n".format(email, site)

        return output

    def write_results_to_zip(self, results):
        # now = time.time().strftime("%d.%m.%Y %H:%M:%S")
        now = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(time.time()))

        if len(results) == 0:
            self.logger.info("No results were found")
            return None

        zip_filename = "{}_{}.zip".format(self.breach_name, now)

        with zipfile.ZipFile(zip_filename, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for domain in results:
                breach_txt_filename = os.path.join(self.breach_name, "{}_{}.txt".format(self.breach_name, domain))

                formatted_output = self.format_results(results[domain])

                z.writestr(breach_txt_filename, formatted_output)

        return zip_filename


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("breach_name", help="Name for this breach dump. Will be used in title for Threat Central case")
    parser.add_argument("breach_dump", help="Path to breach dump. Can be file or directory. Directory will be recursed")
    parser.add_argument("domain_list", help="List of customer email addresses")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Print verbose debug output")
    args = parser.parse_args()

    if os.path.isfile(args.breach_dump):
        with open(args.breach_dump) as f:
            breach_data = json.load(f)

    bn = BreachNotifier(breach_name=args.breach_name,
                        breach_data=breach_data,
                        verbose=args.verbose)

    with open(args.domain_list) as f:
        domains = [line.strip() for line in f]

    results = bn.search_breach_for_domains(domains)

    zip_fullpath = bn.write_results_to_zip(results)
