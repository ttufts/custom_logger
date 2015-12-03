import argparse
import json
import re
import logging
from datetime import datetime, timedelta
import threading
import Queue
import os
import progressbar
import collections
import tldextract

class ZeusSearch:
    relevant_types = [
        "HTTP request",
        "HTTPS request",
        "Grabbed data [HTTP(S)]",
        "POP3 login"
    ]
    max_threads = 10
    DIVIDER = "========================================"

    CC_REGEX = "(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|(?:2131|1800|35\d{3})\d{11})"

    user_id_detection_pairs = [
        ("custid=", "custid=(?: )*(.*)"),
        ("username=", "username=(?: )*(.*)"),
        ("nutzername=", "nutzername=(?: )*(.*)"),
        ("userid=", "userid=(?: )*(.*)"),
        ("Email=", "Email=(?: )*(.*)"),
        ("id=", "id=([0-9]*)"),
        ("login_email=", "login_email=(?: )*(.*)"),
        ("loginfmt=", "loginfmt=(?: )*(.*)"),
        ("client_id=", "client_id=(?: )*(.*)"),
        ("login=", "login=(?: )*(.*)"),
        ("user=", "user=(?: )*(.*)")
    ]


    def __init__(self,
                 output_dir,
                 zeus_path="/extraspace/botnet-data",
                 multi=False,
                 cache_file=None,
                 debug_mode=False,
                 verbose=False):
        self.LOG_FORMAT = ("%(asctime)s | %(levelname)-8s| {0: <25} |"
                           " %(message)s".format(self.__class__.__name__))
        self.verbose = verbose
        self.setup_logger()

        if debug_mode:
            self.logger.warning(("Warning: debug mode on. This will result in "
                                "PII being exported to output files and will "
                                "consume more memory during initialization"))
        self.debug_mode = debug_mode
        self.cache_file = cache_file
        self.multi = multi
        self.output_dir = output_dir

        self.zeus_path = zeus_path
        self.zeus_data = {}
        self.cache = {}

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
        for search_term in search_terms:
            if "source_line" in hb:
                if search_term in hb["source_line"]:
                    return search_term
            else:
                return None

    def search_source_lines(self, search_terms):
        # results = {k: {} for k in search_terms}
        results = {}

        if not self.verbose:
            print "Performing search"
            pbar = progressbar.ProgressBar(maxval=len(self.zeus_data)).start()

        for i, report_file in enumerate(self.zeus_data):
            for bot_id in self.zeus_data[report_file]:
                bot_report = self.zeus_data[report_file][bot_id]

                for hb in bot_report["heart_beats"]:
                    found_term = self.search_hb(search_terms, hb)
                    if found_term:
                        if found_term not in results:
                            results[found_term] = {}
                        if report_file in results[found_term]:
                            results[found_term][report_file]["heart_beats"].append(hb)
                        else:
                            results[found_term][report_file] = {}
                            results[found_term][report_file]["heart_beats"] = [hb]
                            results[found_term][report_file]["ip_addresses"] = []
                            results[found_term][report_file]["user_ids"] = []
                        if "ip_address" in hb:
                            results[found_term][report_file]["ip_addresses"].append(hb["ip_address"])
                        if "user_id" in hb:
                            results[found_term][report_file]["user_ids"].append(hb["user_id"])
            if not self.verbose:
                pbar.update(i)

        if not self.verbose:
            pbar.finish()

        return results

    def collect_stats(self):
        stats = {}
        stats["credit_card_count"] = 0
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
                            stats["email_records"].add(hb["email_address"])
                        if hb["type"] in ["HTTP request", "HTTPS request"]:
                            fullurl = None
                            url = tldextract.extract(hb["source_line"])

                            if url.subdomain:
                                fullurl = '.'.join(url[:3])
                            elif url.domain and url.suffix:
                                fullurl = url.domain+'.'+url.suffix
                            else:
                                fullurl = url.domain

                            if fullurl:
                                all_domains.append(fullurl)


                    if "ip_address" in hb:
                        stats["ips"].add(hb["ip_address"])

                    if "credit_cards" in hb:
                        stats["credit_card_count"] += hb["credit_cards"]

            if not self.verbose:
                pbar.update(i)

        stats["ips"] = list(stats["ips"])
        stats["email_records"] = list(stats["email_records"])

        domcount = collections.Counter(all_domains)
        stats["domain_records"] = domcount.most_common(100)

        stats["summary"] = {}
        stats["summary"]["bot_count"] = len(stats["all_bots"])
        stats["summary"]["email_count"] = len(stats["email_records"])
        stats["summary"]["credit_card_count"] = stats["credit_card_count"]
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

    def strip_email_password(self, line):
        email_regex = "pop3://.*:(.*)@.*"
        email_blank = "XXXXX"
        m = re.findall(email_regex, line)
        if len(m) == 1:
            pword = m[0]
            return line.replace(pword, email_blank)
        else:
            return line

    def parse_bot_heartbeat(self, hb_lines, time_cutoff=None):
        data = {}
        hb_type = None

        if self.debug_mode:
            data["hb_lines"] = hb_lines

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
                data["email_address"] = self.strip_email_password(line.strip())

            # Get bot ID
            if line.startswith("Bot ID:"):
                m = re.findall("Bot ID:(?: )*(.*)", line.strip())

                data["bot_id"] = m[0]

            # Get IP lines
            if line.startswith("IPv4:"):
                m = re.findall("IPv4:(?: )*(.*)", line.strip())

                data["ip_address"] = m[0]

            # Get user_id lines (often found in bank HTTPS grabbed data)
            if "user" in line.lower():
                data["possible_user_line"] = line


            for linestart, regex in self.user_id_detection_pairs:
                if line.startswith(linestart):
                    m = re.findall(regex, line.strip())

                    data["user_id"] = m[0]

            # Search for Credit Card numbers:
            credit_cards = re.findall(self.CC_REGEX, line.strip())
            if credit_cards is not None and len(credit_cards) > 0:
                data["credit_cards"] = len(credit_cards)

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

    def multi_worker(self):
        filepath, time_cutoff = self.thread_queue.get()
        self.zeus_data[filepath] = self.parse_file_data(filepath, time_cutoff=time_cutoff)
        self.thread_queue.task_done()

        if not self.verbose:
            self.init_tracking += 1
            self.pbar.update(self.init_tracking)

    def init_thread_pool(self, max_threads=100):
        for i in range(max_threads):
            t = threading.Thread(target=self.multi_worker)
            t.setDaemon(True)
            self.thread_pool.append(t)
            t.start()

    def init_zeus_data_multi(self, time_cutoff=None):
        self.init_thread_pool()

        all_files = self.enumerate_zeus_files()

        if not self.verbose:
            self.init_tracking = 0
            self.pbar = progressbar.ProgressBar(maxval=len(all_files)).start()

        for filepath in all_files:
            self.thread_queue.put((filepath, time_cutoff))

        self.thread_queue.join()

        if not self.verbose:
            self.pbar.finish()
        #     thread = threading.Thread(target=self.parse_file_data,
        #                               args=[filepath],
        #                               kwargs={"time_cutoff": time_cutoff})
        #     thread.start()
        #     self.thread_pool.append(thread)
        #
        # while True:
        #     if len(self.zeus_data.keys()) < len(self.thread_pool):
        #         filepath, thread_result = self.thread_queue.get()
        #         self.zeus_data[filepath] = thread_result
        #     else:
        #         break



    def output_search_results(self, search_results, json_output=False):
        curr_date = datetime.now().strftime("%d.%m.%Y")
        for search_term in search_results:
            dir_path = os.path.join(self.output_dir, search_term)
            if not os.path.isdir(dir_path):
                os.makedirs(dir_path)

            if self.debug_mode:
                output_file = "{}_{}_DEBUG.txt".format(curr_date, search_term)
            else:
                output_file = "{}_{}.txt".format(curr_date, search_term)
            output_path = os.path.join(dir_path, output_file)

            with open(output_path, "w") as f:
                if json_output:
                    json.dump(search_results[search_term],
                              f,
                              indent=4,
                              separators=(",", ": "))
                else:
                    for report_file in search_results[search_term]:
                        path, fname = os.path.split(report_file)
                        c2 = fname.replace("-", "/")
                        ip_address = None
                        user_id = None
                        report = search_results[search_term][report_file]
                        if "ip_addresses" in report:
                            ip_address = report["ip_addresses"]
                        if "user_ids" in report:
                            user_id = report["user_ids"]
                        hb_string = json.dumps(
                                             report["heart_beats"],
                                             indent=4,
                                             separators=(",", ": ")
                                             )
                        output_line = ("C2: {report_file}\t"
                                       "IP Addresses: {ip_address}\t"
                                       "User IDs: {user_id}\n"
                                       "Heartbeats: {heartbeats}\n").format(
                                       report_file=c2,
                                       ip_address=ip_address,
                                       user_id=user_id,
                                       heartbeats=hb_string
                                       )
                        f.write(output_line)

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

    def read_cache(self):
        if not os.path.isfile(self.cache_file):
            self.logger.warning("Cache file doesn't exist yet")
            self.cache = {}
            return

        try:
            with open(self.cache_file) as f:
                self.cache = json.load(f)
        except:
            self.logger.error("Unable to read cache file.")
            self.cache = {}

    def check_cache(self, time_cutoff):
        if time_cutoff is None:
            time_cutoff = "ALL"
        else:
            time_cutoff = time_cutoff.strftime("%d.%m.%Y")

        try:
            self.cache[self.zeus_path][time_cutoff]
            return True
        except KeyError:
            return False

    def init_from_cache(self, time_cutoff):
        if time_cutoff is None:
            time_cutoff = "ALL"
        else:
            time_cutoff = time_cutoff.strftime("%d.%m.%Y")

        self.zeus_data = self.cache[self.zeus_path][time_cutoff]

        if "debug_mode" in self.cache[self.zeus_path][time_cutoff] and self.cache[self.zeus_path][time_cutoff]["debug_mode"]:
            self.debug_mode = True

        del self.zeus_data["debug_mode"]

        if self.debug_mode:
            self.logger.warning(("Warning: cache was initialized with debug "
                                 "mode on. This will result in PII being "
                                 "exported to output files and will consume "
                                 "more memory during initialization"))


    def update_cache(self, time_cutoff):
        if time_cutoff is None:
            time_cutoff = "ALL"
        else:
            time_cutoff = time_cutoff.strftime("%d.%m.%Y")

        if self.zeus_path not in self.cache:
            self.cache[self.zeus_path] = {}

        self.cache[self.zeus_path][time_cutoff] = self.zeus_data
        if self.debug_mode:
            self.cache[self.zeus_path][time_cutoff]["debug_mode"] = True
        else:
            self.cache[self.zeus_path][time_cutoff]["debug_mode"] = False

        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=4, separators=(",", ": "))

        del self.zeus_data["debug_mode"]


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
                        help=("To specify a timespan when parsing data files. "
                        "Will ignore anything older than this date"))
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        default=False,
                        help="Print verbose debug output")
    parser.add_argument("-o",
                        "--output_dir",
                        default=".",
                        help="Output directory")
    parser.add_argument("-j",
                        "--json",
                        action="store_true",
                        default=False,
                        help="JSON output")
    parser.add_argument("-c",
                        "--cache_file",
                        default=".zeus_cache",
                        help="Cache indexed zeus data")
    parser.add_argument("-i",
                        "--initialize",
                        action="store_true",
                        default=False,
                        help="Force re-initialize")
    parser.add_argument("-x",
                        "--debug_mode",
                        action="store_true",
                        default=False,
                        help="Keep all heartbeat lines (Warning, will output PII and use much more memory)")

    args = parser.parse_args()

    zs = ZeusSearch(args.output_dir,
                    args.botnet_data,
                    multi=args.multithreaded,
                    cache_file=args.cache_file,
                    debug_mode=args.debug_mode,
                    verbose=args.verbose)

    if args.timespan is None:
        time_cutoff = None
    else:
        time_cutoff = datetime.strptime(args.timespan, "%d.%m.%Y")

    if args.initialize:
        zs.init_zeus_data(time_cutoff)
        zs.update_cache(time_cutoff)

    else:
        zs.logger.info("Reading cache {}".format(zs.cache_file))
        zs.read_cache()

        if zs.check_cache(time_cutoff):
            zs.logger.info("Initializing from cache {}".format(zs.cache_file))
            zs.init_from_cache(time_cutoff)
        else:
            zs.logger.info("Data for {} and {} not found in cache, initializing".format(zs.zeus_path, time_cutoff))
            zs.init_zeus_data(time_cutoff)
            zs.logger.info("Updating cache with data for {} and {}".format(zs.zeus_path, time_cutoff))
            zs.update_cache(time_cutoff)


    # Search through Source lines
    if args.find:
        searchlist = []

        if os.path.isfile(args.find):
            zs.logger.debug("Reading file {} for search terms"
                            .format(args.find))

            with open(args.find) as f:
                searchlist = [term.strip() for term in f]
        else:
            zs.logger.debug("Using {} as search term"
                            .format(args.find, args.find))
            searchlist.append(args.find)

        search_results = zs.search_source_lines(searchlist)

        output_dir = zs.output_search_results(search_results,
                                              json_output=args.json)

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