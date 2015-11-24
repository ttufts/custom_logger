import argparse
import json
import logging
import os
import zipfile
from pprint import pprint
from time import sleep

from BreachNotifier import BreachNotifier
from gmail_monitor.GmailMonitor import GmailMonitor

class BreachMonitor:
    def __init__(self,
                 breach_name,
                 breach_data,
                 client_secret_file,
                 verbose=False):
        self.verbose = verbose
        self.setup_logger()

        self.breach_name = breach_name
        self.breach_data = breach_data
        self.download_dir = ".breach_domain_downloads"
        self.client_secret_file = client_secret_file
        self.credential_file = u"gmail-python-breach-notifier.json"

        if not os.path.isdir(self.download_dir):
            os.makedirs(self.download_dir)

        breach_notifier_label = u"Label_8701994825581701819"
        breach_notifier_processed_label = u"Label_4759391483624140280"

        self.gm = GmailMonitor(unprocessed_label=breach_notifier_label,
                               processed_label=breach_notifier_processed_label,
                               application_name=u"Breach Notifier Gmail Monitor",
                               client_secret_file=self.client_secret_file,
                               credential_file=self.credential_file,
                               verbose=self.verbose)

        self.bn = BreachNotifier(breach_name=self.breach_name,
                                 breach_data=self.breach_data,
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

    def get_new_files_from_email(self):
        return list(self.gm.poll_for_new_emails(self.download_dir, ".txt"))

    def get_domain_from_email(self, email):
        username, domain = email.split("@")

        return domain.strip().lower()

    def get_domains_from_file(self, filepath):
        domains = []
        with open(filepath) as f:
            for line in f:
                if "@" in line:
                    domain = self.get_domain_from_email(line.strip())
                else:
                    domain = line.strip()
                domains.append(domain)

        self.logger.info("Found {} domains in file {}".format(len(domains), filepath))

        return domains

    def send_zip_in_email(self, email_info, zip_fullpath):
        path, attachment_filename = os.path.split(email_info["attachment_path"])
        email_subject = "{}: Results from file {}".format(self.breach_name,
                                                          attachment_filename)

        email_body = ("Attached you will find a zip file containing results "
                      "files for all domains included in the list sent in "
                      "the previous email.\n"
                      "Received filename: {}\n"
                      "Breach Name: {}\n").format(attachment_filename, self.breach_name)

        self.gm.send_email(email_info["reply_to"],
                           email_info["subject"],
                           email_body,
                           [zip_fullpath])
        self.logger.info("Sent email to {}".format(email_info["reply_to"]))

    def process_new_emails(self):
        for email_info in self.get_new_files_from_email():
            self.logger.info("Downloaded file {} from email".format(email_info["attachment_path"]))
            domains = self.get_domains_from_file(email_info["attachment_path"])

            results = self.bn.search_breach_for_domains(domains)

            zip_fullpath = self.bn.write_results_to_zip(results)

            self.send_zip_in_email(email_info, zip_fullpath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("breach_name", help="Name for this breach dump. Will be used in title for Threat Central case")
    parser.add_argument("breach_dump", help="Path to breach dump. Can be file or directory. Directory will be recursed")
    parser.add_argument("-c", "--client_secret_file", default=u"client_secret_breach_notifier.json", help="Path to client secret file")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Print verbose debug output")
    args = parser.parse_args()

    if os.path.isfile(args.breach_dump):
        with open(args.breach_dump) as f:
            gl_webmail_data = json.load(f)
            breach_data = gl_webmail_data["found"]

    bm = BreachMonitor(breach_name=args.breach_name,
                       breach_data=breach_data,
                       client_secret_file=args.client_secret_file,
                       verbose=args.verbose)

    while True:
        bm.process_new_emails()
        sleep(1)
