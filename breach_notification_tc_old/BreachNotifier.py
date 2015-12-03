import argparse
import json
import logging
import os
import zipfile

from threat_central.APICore import APICore
from threat_central.User import User
from threat_central.Case import Case
from threat_central.Search import Search
from BreachSearcher import BreachSearcher
from BreachCustomerManager import BreachCustomerManager

class BreachNotifier:
    HPSR_COMMUNITY_NAME = "HP Security Research"

    def __init__(self, tc_config, breach_path, cache_file, verbose=False):
        self.verbose = verbose
        self.tc_config = tc_config
        self.breach_path = breach_path
        self.tmp_file_location = ".tmpfile"

        self.cache_file = "{}.{}.json".format(cache_file, self.get_server_nick())

        self.customer_domains = set()
        self.breach_files = []
        self.community_by_domain = {}
        self.domain_blacklist = []

        self.setup_logger()

        self.tc_search = Search(self.tc_config, verbose=self.verbose)

        self.logger.debug("Enumerating breach files")
        self.enumerate_breach_files()

        self.logger.debug("Initializing BreachSearcher instance")
        self.bs = BreachSearcher(breach_files = self.breach_files, logger=self.logger, verbose=self.verbose)

        self.logger.debug("Initializing BreachCustomerManager instance")
        self.bcm = BreachCustomerManager(tc_config=self.tc_config, logger=self.logger, verbose=self.verbose)

        self.logger.debug("Enumerating searchable domains from TC customer email addresses")
        self.get_customer_domains()


    def get_server_nick(self):
        server_nick = self.tc_config["tc_server"].replace("https://", "")
        server_nick = server_nick.replace("http://", "")
        if server_nick.endswith("/"):
            server_nick = server_nick[:-1]
        server_nick = server_nick.replace("/", "_")

        return server_nick

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


    def enumerate_breach_files(self):
        if os.path.isfile(self.breach_path):
            self.breach_files.append(self.breach_path)

        if os.path.isdir(self.breach_path):
            for root, dirs, files in os.walk(self.breach_path):
                for filename in files:
                    fullpath = os.path.join(root, filename)
                    self.breach_files.append(fullpath)


    def load_cache_file(self):
        try:
            with open(self.cache_file) as f:
                cache = json.load(f)

            try:
                self.community_by_domain = cache["community_by_domain"]
                self.domain_blacklist = cache["domain_blacklist"]
            except:
                pass

            # Put other cache stuff here as needed

        except IOError:
            pass

    def write_cache_file(self):
        cache = {}
        cache["community_by_domain"] = self.community_by_domain
        cache["domain_blacklist"] = self.domain_blacklist

        # Put other cache stuff here as needed

        with open(self.cache_file, "w") as f:
            json.dump(cache, f, sort_keys=True, indent=4, separators=(',', ': '))


    def update_community_database(self, user, domain):
        self.load_cache_file()

        try:
            if self.community_by_domain[domain] is None:
                raise KeyError
        except KeyError:
            community = self.prompt_for_community(user, domain)
            self.community_by_domain[domain] = community

        self.write_cache_file()


    def prompt_for_community(self, user, domain):
        full_name = "{} {}".format(user.first_name, user.last_name)
        user_communities = []
        for community_dict in user.company_dict["communities"]:
            community_slim = {}
            community_slim["id"] = community_dict["resourceId"]
            community_slim["name"] = community_dict["name"]
            user_communities.append(community_slim)

        while True:
            print full_name
            print domain
            for community in user_communities:
                print community["id"], community["name"]

            print "Enter the resourceId of the community to notify for this user/domain (Type 'skip' to skip this user)"
            userinput = raw_input().strip()

            if userinput in [community["id"] for community in user_communities]:
                return userinput
            elif userinput == "skip":
                return None
            elif userinput in ["NA", "N/A", "n/a", "na"]:
                return ""
            else:
                print userinput
                print "ResourceId entered is not valid for this user"


    def get_domain_from_email(self, email):
        username, domain = email.split("@")

        return domain.strip().lower()


    def get_hpsr_community_id(self):
        return self.tc_search.search_for_community(self.HPSR_COMMUNITY_NAME, exact_match=True)

    def get_customer_domains(self):
        for user in self.bcm.users:
            domain = self.get_domain_from_email(user.email)

            if domain in self.domain_blacklist:
                continue

            self.update_community_database(user, domain)

            self.customer_domains.add(domain)

        return self.customer_domains


    def search_breach_for_domain(self, domain):
        results = self.bs.search_breach_for_domain(domain)

        return results

    def write_results_to_zip(self, breach_name, domain, data, outdir="."):
        data_text = "\n".join(data)
        breach_dump_filename = "{}_{}.txt".format(breach_name, domain)
        breach_zip_filename = os.path.join(outdir, "{}_{}.zip".format(breach_name, domain))

        with zipfile.ZipFile(breach_zip_filename, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr(breach_dump_filename, data_text)

        return breach_zip_filename

    def write_results_to_txt(self, breach_name, domain, data, outdir="."):
        data_text = "\n".join(data)
        breach_txt_filename = os.path.join(outdir, "{}_{}.txt".format(breach_name, domain))

        with open(breach_txt_filename, "w") as f:
            f.write(data_text)

        return breach_txt_filename

    def create_breach_case(self, breach_name, domain, data):
        tmp_file = False

        community = self.community_by_domain[domain]
        hpsr_community = self.get_hpsr_community_id()

        if community and community != "":
            shareWith = [community, hpsr_community]
        else:
            shareWith = [hpsr_community]

        title = "Breach notification for {breach} for {domain}".format(breach=breach_name, domain=domain)

        description = ("The following email addresses from {} were found in the "
                       "{} breach. These accounts on your domain may have been "
                       "compromised along with the breach.\n").format(domain, breach_name)

        breach_zip_filename = self.write_results_to_zip(breach_name, domain, data)

        self.logger.info("Creating case for {} users".format(domain))
        self.logger.info("{} emails found in breach from {}".format(len(data), domain))
        user_input = raw_input("Submit to TC (Y/n)")
        if user_input in ["y", "Y", ""]:
            case = Case(self.tc_config, title=title, description=description, shareWith=[hpsr_community, community], allow_duplicate=True)
            # case = Case(self.tc_config, title=title, description=description, shareWith=[hpsr_community, community])

            case.add_attachment(breach_zip_filename, att_type="application/zip")

            return case.link
        else:
            self.logger.info("Not submitting case")
            return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("tc_config", help="config file with Threat Central authentication")
    parser.add_argument("breach_name", help="Name for this breach dump. Will be used in title for Threat Central case")
    parser.add_argument("breach_dump", help="Path to breach dump. Can be file or directory. Directory will be recursed")
    parser.add_argument("-c", "--cache_file", default=".cache_file", help="Location of cache file")
    parser.add_argument("-d", "--dump", help="Dump results to files")
    parser.add_argument("-s", "--simulate", action="store_true", default=False, help="Parse the breach and print results, but don't submit to TC")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Print verbose debug output")
    args = parser.parse_args()

    config = APICore.parse_config(args.tc_config)

    bn = BreachNotifier(config, args.breach_dump, verbose=args.verbose, cache_file=args.cache_file)

    bn.logger.info("Found {} domains to search for in {} files.".format(len(bn.customer_domains), len(bn.breach_files)))
    for i, domain in enumerate(bn.customer_domains):
        bn.logger.debug("Searching for {}".format(domain))
        domain_results = bn.search_breach_for_domain(domain)

        if len(domain_results) > 0:
            if not args.simulate and not args.dump:
                bn.logger.debug("Creating breach case for domain {} with {} domains".format(domain, len(domain_results)))
                bn.logger.info(bn.create_breach_case(args.breach_name, domain, domain_results))
            if args.simulate:
                bn.logger.info("Domain: {}".format(domain))
                bn.logger.info(str(domain_results))
                bn.logger.info("{} total results: {}".format(domain, len(domain_results)))
            if args.dump:
                if not os.path.isdir(args.dump):
                    os.makedirs(args.dump)
                zip_file = bn.write_results_to_txt(args.breach_name, domain, domain_results, args.dump)
                bn.logger.info("Wrote file: {}".format(zip_file))
        else:
            bn.logger.debug("No results found for domain {}".format(domain))
