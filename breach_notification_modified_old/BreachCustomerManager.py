import argparse
import json
import logging
import os

from threat_central.APICore import APICore
from threat_central.User import User
from threat_central.Search import Search

class BreachCustomerManager:
    def __init__(self, tc_config, logger=None, verbose=False):
        self.verbose = verbose
        self.logger = logger
        self.tc_config = tc_config
        self.users = []

        if logger is None:
            self.setup_logger()


        self.logger.info("Getting Threat Central users")
        self.get_threat_central_users()

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


    def get_threat_central_users(self):
        s = Search(self.tc_config, verbose=self.verbose)
        for user in s.get_users():
            u = User(self.tc_config, existing_dict=user, verbose=self.verbose)
            self.users.append(u)

        return self.users


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("tc_config", help="config file with Threat Central authentication")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Print verbose debug output")
    args = parser.parse_args()

    config = APICore.parse_config(args.tc_config)

    bcm = BreachCustomerManager(config, verbose=args.verbose)

    for user in bcm.get_threat_central_users():
        if "yahoo.com" in user.email or "gmail.com" in user.email:
            print user.first_name, user.last_name, user.email, user.company_dict["name"]
