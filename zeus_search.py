import argparse
import json
import re
import logging
from time import sleep
from time import time
from datetime import datetime, timedelta
import tldextract
import threading
import Queue
import os
import progressbar
import collections

class ZeusSearch:
    relevant_types = [
        "HTTP request",
        "HTTPS request",
        "Grabbed data [HTTP(S)]",
        "POP3 login"
    ]
    max_threads = 10
    DIVIDER = "========================================"

    def __init__(self,
                 output_dir,
                 zeus_path="/extraspace/botnet-data",
                 multi=False,
                 verbose=False):
        self.LOG_FORMAT = ("%(asctime)s | %(levelname)-8s| {0: <25} |"
                      " %(message)s".format(self.__class__.__name__))
        self.verbose = verbose
        self.setup_logger()

        self.multi = multi
        self.output_dir = output_dir

        self.zeus_path = zeus_path
        self.zeus_data = {}

        if self.multi:
            self.thread_pool = []
            self.thread_queue = Queue.Queue()


    def setup_logger(self):
        self.logger = logging.getLogger()

        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(self.LOG_FORMAT)

        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        if self.verbose:
            ch.setLevel(logging.DEBUG)
        else:
            ch.setLevel(logging.INFO)
        self.logger.addHandler(ch)


    def search_hb(self, search_terms, hb):
        terms_in_hb = []

        for search_term in search_terms:
            if "source_line" in hb:
                if search_term in hb["source_line"]:
                    return search_term
            else:
                return None


    def search_source_lines(self, search_terms):
        results = {k: {} for k in search_terms}

        if not self.verbose:
            print "Performing search"
            pbar = progressbar.ProgressBar(maxval=len(self.zeus_data)).start()

        for i, report_file in enumerate(self.zeus_data):
            for bot_id in self.zeus_data[report_file]:
                bot_report = self.zeus_data[report_file][bot_id]

                for hb in bot_report["heart_beats"]:
                    found_term = self.search_hb(search_terms, hb)
                    if found_term:
                        if report_file in results[found_term]:
                            results[found_term][report_file].append(hb)
                        else:
                            results[found_term][report_file] = [hb]
            if not self.verbose:
                pbar.update(i)

        if not self.verbose:
            pbar.finish()

        return results


    def collect_stats(self):
        stats = {}
        stats["all_bots"] = []
        stats["email_records"] = set()
        all_domains = []
        stats["ips"] = set()

        if not self.verbose:
            print "Collecting statistics"
            pbar = progressbar.ProgressBar(maxval=len(self.zeus_data)).start()


        for i, report_file in enumerate(self.zeus_data):
            for bot_id in self.zeus_data[report_file]:
                bot_report = self.zeus_data[report_file][bot_id]

                stats["all_bots"].append(bot_report)

                for hb in bot_report["heart_beats"]:
                    if "type" in hb:
                        if hb["type"] == "POP3 login":
                            stats["email_records"].add(hb["source_line"])
                        if hb["type"] in ["HTTP request", "HTTPS request"]:
                            all_domains.append(hb["source_line"])

                    if "ip_address" in hb:
                        stats["ips"].add(hb["ip_address"])

            if not self.verbose:
                pbar.update(i)

        stats["ips"] = list(stats["ips"])
        stats["email_records"] = list(stats["email_records"])

        domcount=collections.Counter(all_domains)
        stats["domain_records"] = domcount.most_common(100)

        stats["summary"] = {}
        stats["summary"]["bot_count"] = len(stats["all_bots"])
        stats["summary"]["email_count"] = len(stats["email_records"])
        stats["summary"]["ip_count"] = len(stats["ips"])

        if not self.verbose:
            pbar.finish()

        return stats


    def split_heartbeats(self, lines):
        heart_beats = []

        this_hb = []

        for line in lines:
            if line.startswith(self.DIVIDER) and len(this_hb) > 0:
                heart_beats.append(this_hb)
                this_hb = []

            this_hb.append(line)

        return heart_beats


    def split_bot_reports(self, lines):
        bot_reports = []

        this_bot = []

        last_line = ""

        for line in lines:
            # Find bot start
            if (last_line.startswith(self.DIVIDER) and
                    line.startswith("Bot ID:") and
                    len(this_bot) > 0):
                bot_reports.append(this_bot)
                this_bot = []

                this_bot.append(last_line)

            this_bot.append(line)

            last_line = line
        return bot_reports


    def parse_bot_heartbeat(self, hb_lines, time_cutoff=None):
        data = {}
        hb_type = None

        for line in hb_lines:
            # Get report time
            if line.startswith("Report time:"):
                m = re.findall("Report time:(?: )*(.*)", line.strip())

                if len(m) == 0:
                    continue

                report_time = m[0]

                report_time = datetime.strptime(report_time,
                                                        "%d.%m.%Y %H:%M:%S")

                if time_cutoff:
                    if report_time < time_cutoff:
                        return None

                data["report_time"] = report_time.strftime("%d.%m.%Y %H:%M:%S")

            # Get Type
            if line.startswith("Type:"):
                m = re.findall("Type:(?: )*(.*)", line.strip())

                hb_type = m[0]
                if hb_type in self.relevant_types:
                    data["type"] = hb_type

            # Get source line
            if line.startswith("Source:"):
                m = re.findall("Source:(?: )*(.*)", line.strip())
                source = m[0]

            # Only keep certain source lines
            if hb_type and hb_type in self.relevant_types:
                data["source_line"] = source

            if line.startswith("pop3"):
                data["source_line"] = line.strip()

            # Get bot ID
            if line.startswith("Bot ID:"):
                m = re.findall("Bot ID:(?: )*(.*)", line.strip())

                data["bot_id"] = m[0]

            # Get IP lines
            if line.startswith("IPv4:"):
                m = re.findall("IPv4:(?: )*(.*)", line.strip())

                data["ip_address"] = m[0]

        return data


    def parse_bot_report(self, lines, time_cutoff=None):
        bot_report = {}
        bot_report["heart_beats"] = []

        heart_beats = self.split_heartbeats(lines)

        # print "Found {} heart beats".format(len(heart_beats))

        for hb in heart_beats:
            hb_info = self.parse_bot_heartbeat(hb, time_cutoff=time_cutoff)

            # Don't bother with older heartbeats
            if hb_info is {} or hb_info is None:
                continue

            if "bot_id" in hb_info:
                bot_report["bot_id"] = hb_info["bot_id"]

            bot_report["heart_beats"].append(hb_info)

        return bot_report


    def parse_file_data(self, filepath, time_cutoff=None):
        file_data = {}

        with open(filepath) as f:
            lines = f.readlines()

        bot_reports = self.split_bot_reports(lines)

        self.logger.debug("Found {} bot reports in {}"
                          .format(len(bot_reports), filepath))

        for report in bot_reports:
            report_info = self.parse_bot_report(report,
                                                time_cutoff=time_cutoff)
            try:
                bot_id = report_info["bot_id"]
            except KeyError:
                continue

            file_data[bot_id] = report_info

        if self.multi:
            self.thread_queue.put((filepath, file_data))
        else:
            return file_data


    def init_zeus_data(self, time_cutoff=None):
        self.logger.debug("Initializing Zeus data from {}"
                          .format(self.zeus_path))

        if self.multi:
            self.init_zeus_data_multi(time_cutoff)
        else:
            self.init_zeus_data_single(time_cutoff)


    def enumerate_zeus_files(self):
        zeus_files = []

        if os.path.isdir(self.zeus_path):
            for root, dirs, files in os.walk(self.zeus_path):
                for filename in files:
                    full_path = os.path.join(root, filename)
                    zeus_files.append(full_path)
        elif os.path.isfile(self.zeus_path):
            zeus_files.append(self.zeus_path)

        return zeus_files


    def init_zeus_data_single(self, time_cutoff=None):
        zeus_files = self.enumerate_zeus_files()
        if not self.verbose:
            print "Reading botnet data from {}".format(self.zeus_path)
            pbar = progressbar.ProgressBar(maxval=len(zeus_files)).start()
        for i, filepath in enumerate(zeus_files):
            data = self.parse_file_data(filepath, time_cutoff=time_cutoff)
            self.zeus_data[filepath] = data
            if not self.verbose:
                pbar.update(i)

        if not self.verbose:
            pbar.finish()


    def init_zeus_data_multi(self, time_cutoff=None):
        for filepath in self.enumerate_zeus_files():
            thread = threading.Thread(target=self.parse_file_data,
                                      args=[filepath],
                                      kwargs={"time_cutoff": time_cutoff})
            thread.start()
            self.thread_pool.append(thread)

        while True:
            if len(self.zeus_data.keys()) < len(self.thread_pool):
                filepath, thread_result = self.thread_queue.get()
                self.zeus_data[filepath] = thread_result
            else:
                break


    def output_search_results(self, search_results):
        curr_date = datetime.now().strftime("%d.%m.%Y")
        for search_term in search_results:
            dir_path = os.path.join(self.output_dir, search_term)
            if not os.path.isdir(dir_path):
                os.makedirs(dir_path)

            output_file = "{}_{}.txt".format(curr_date, search_term)
            output_path = os.path.join(dir_path, output_file)

            with open(output_path, "w") as f:
                json.dump(search_results[search_term],
                          f,
                          indent=4,
                          separators=(",", ": "))

        return self.output_dir

    def output_stats(self, stats):
        stat_types = [
            "summary",
            "ips",
            "all_bots",
            "email_records",
            "domain_records"
        ]

        curr_date = datetime.now().strftime("%d.%m.%Y")

        stats_dir = os.path.join(self.output_dir, "stats")
        if not os.path.isdir(stats_dir):
            os.makedirs(stats_dir)

        for stat_type in stat_types:
            output_file = "{}_{}.txt".format(curr_date, stat_type)
            output_path = os.path.join(stats_dir, output_file)

            with open(output_path, "w") as f:
                json.dump(stats[stat_type],
                          f,
                          indent=4,
                          separators=(",", ": "))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-m",
                        "--multithreaded",
                        action="store_true",
                        default=False,
                        help="Multithread the parsing of files")
    parser.add_argument("-d",
                        "--botnet_data",
                        default="/extraspace/botnet-data",
                        help="Botnet data path")
    parser.add_argument("-f",
                        "--find",
                        help="Run against a list of search terms")
    parser.add_argument("-s",
                        "--statistics",
                        action="store_true",
                        default=False,
                        help="Run statistics")
    parser.add_argument("-t",
                        "--timespan",
                        help=("To run historic stats since day.month.year "
                              "(Default: today - 30 days)"))
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        default=False,
                        help="Print verbose debug output")
    parser.add_argument("-o",
                        "--output_dir",
                        default=".",
                        help="Output directory")

    args = parser.parse_args()

    zs = ZeusSearch(args.output_dir,
                    args.botnet_data,
                    multi=args.multithreaded,
                    verbose=args.verbose)

    if args.timespan is None:
        time_cutoff = datetime.now() - timedelta(days=30)
    else:
        time_cutoff = datetime.strptime(args.timespan, "%d.%m.%Y")

    zs.init_zeus_data(time_cutoff)

    # Search through Source lines
    if args.find:
        searchlist = []

        if os.path.isfile(args.find):
            zs.logger.debug("Reading file {} for search terms"
                           .format(args.find))

            with open(filename) as f:
                searchlist = [term.strip() for term in f]
        else:
            zs.logger.debug("Using {} as search term"
                           .format(args.find, args.find))
            searchlist.append(args.find)

        search_results = zs.search_source_lines(searchlist)

        output_dir = zs.output_search_results(search_results)

        for search_term in search_results:
            zs.logger.debug("{} results for search term {}".format(
                           len(search_results[search_term]),
                           search_term))

        zs.logger.debug("Writing output to {}".format(output_dir))

    if args.statistics:
        stats = zs.collect_stats()
        zs.output_stats(stats)

    if not args.statistics and args.find is None:
        parser.print_help()
