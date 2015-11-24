import argparse
import json
import logging
import os
import collections
import re


class BreachHistogram:
    HPSR_COMMUNITY_NAME = "HP Security Research"

    def __init__(self, breach_path, verbose=False):
        self.verbose = verbose
        self.breach_path = breach_path
        self.tmp_file_location = ".tmpfile"

        self.breach_files = []

        self.setup_logger()

        self.logger.debug("Enumerating breach files")
        self.enumerate_breach_files()

    def setup_logger(self):
        self.logger = logging.getLogger()

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
        try:
            username, domain = email.split("@")

            return domain.strip().lower()
        except:
            return None
            print u"Unable to split domain from {}".format(email)

    def enumerate_breach_files(self):
        if os.path.isfile(self.breach_path):
            self.breach_files.append(self.breach_path)

        if os.path.isdir(self.breach_path):
            for root, dirs, files in os.walk(self.breach_path):
                for filename in files:
                    fullpath = os.path.join(root, filename)
                    self.breach_files.append(fullpath)

    def get_domains(self):
        all_domains = []
        for breach_file in self.breach_files:
            with open(breach_file) as f:
                breach_content = json.load(f)

            for site in breach_content:
                for email_address in breach_content[site]:
                    domain = self.get_domain_from_email(email_address)
                    if domain is not None and domain != "":
                        all_domains.append(domain)

        return all_domains

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("breach_dump", help="Path to breach dump. Can be file or directory. Directory will be recursed")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Print verbose debug output")
    args = parser.parse_args()

    bn = BreachHistogram(args.breach_dump, verbose=args.verbose)

    all_domains = bn.get_domains()

    domcount = collections.Counter(all_domains)

    # with open("country_tlds.json") as f:
    #     country_tlds = json.load(f)
    #
    # for country_tld, country_re in country_tlds.items():
    #     print "Checking {}: {}".format(country_tld, country_re)
    #     with open("./country_codes/{}_domain_count.txt".format(country_tld.replace(".", "")), "w") as f:
    #         for domain, count in domcount.most_common():
    #             if re.match(country_re, domain):
    #                 # print("{}: {}".format(domain.encode("utf-8", "ignore"), count))
    #                 f.write("{}: {}\n".format(domain.encode("utf-8", "ignore"), count))

    with open("twc.com_domain_count.txt", "w") as f:
        for domain, count in domcount.most_common():
            if re.match(".*twc.com$", domain) or re.match(".*twcable.com$", domain):
                # print("{}: {}".format(domain.encode("utf-8", "ignore"), count))
                f.write("{}: {}\n".format(domain.encode("utf-8", "ignore"), count))


    # print domcount
    #
    # labels, values = zip(*domcount.items())
    # indexes = numpy.arange(len(labels))
    # width = 1
    #
    # plt.bar(indexes, values, width)
    # plt.xticks(indexes + width * 0.5, labels)
    # plt.savefig("histogram.png")
    # plt.show()

    # df = pandas.DataFrame.from_dict(domcount, orient='index')
    # df.plot(kind="bar")
