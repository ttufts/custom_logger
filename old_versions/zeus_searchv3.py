import argparse
import json
import re
import logging
from time import sleep
from time import time
from datetime import datetime, timedelta
import tldextract

import os

class ZeusSearch:
    relevant_types = ["HTTP request", "Grabbed data [HTTP(S)]"]

    def __init__(self, zeus_path = "/extraspace/botnet-data"):
        self.zeus_path = zeus_path
        self.zeus_data = {}

    def search_source_lines(self, search_terms, timespan=None):
        results = {}

        if timespan:
            time_cutoff = datetime.now() - timedelta(days=timespan)

        for report_file in self.zeus_data:
            for bot_id in self.zeus_data[report_file]:
                bot_report = self.zeus_data[report_file][bot_id]
                for hb in bot_report["heart_beats"]:
                    if hb < time_cutoff: continue

                    no_source = False
                    for search_term in search_terms:
                        try:
                            if search_term in hb["source_line"]:
                                try:
                                    results[report_file].append(hb["report_time"])
                                except KeyError:
                                    results[report_file] = [hb["report_time"]]
                        except KeyError:
                            no_source = True
                            break
                    if no_source: continue

        return results

    def split_heartbeats(self, lines):
        heart_beats = []

        this_hb = []

        for line in lines:
            if line.startswith("========================================") and len(this_hb) > 0:
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
            if last_line.startswith("========================================") and line.startswith("Bot ID:") and len(this_bot) > 0:
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

                report_time = m[0]

                if time_cutoff:
                    if report_time < time_cutoff: return None

                data["report_time"] = datetime.strptime(report_time, "%d.%m.%Y %H:%M:%S")

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

        return data


    def parse_bot_report(self, lines, time_cutoff=None):
        bot_report = {}
        bot_report["heart_beats"] = []

        heart_beats = self.split_heartbeats(lines)

        # print "Found {} heart beats".format(len(heart_beats))

        for hb in heart_beats:
            hb_info = self.parse_bot_heartbeat(hb, time_cutoff=time_cutoff)

            # Don't bother with older heartbeats
            if hb_info is not None:
                continue

            if "bot_id" in hb_info:
                bot_report["bot_id"] = hb_info["bot_id"]

            bot_report["heart_beats"].append(hb_info)

        return bot_report


    def parse_file_data(self, filepath, timespan=None):
        file_data = {}
        time_cutoff = None
        with open(filepath) as f:
            lines = f.readlines()

        if timespan:
            time_cutoff = datetime.now() - timedelta(days=timespan)

        bot_reports = self.split_bot_reports(lines)

        # print "Found {} bot reports".format(len(bot_reports))

        for report in bot_reports:
            report_info = self.parse_bot_report(report, time_cutoff=time_cutoff)
            try:
                bot_id = report_info["bot_id"]
            except KeyError:
                # print "Somehow there wasn't a bot ID found in a bot report... this should be impossible."
                # print report
                continue
                # raise Exception("Somehow there wasn't a bot ID found in a bot report... this should be impossible.")

            file_data[bot_id] = report_info

        return file_data


    def init_zeus_data(self):
        if os.path.isdir(self.zeus_path):
            for dir_entry in os.listdir(self.zeus_path):
                dir_entry_path = os.path.join(self.zeus_path, dir_entry)
                if os.path.isfile(dir_entry_path):
                    self.zeus_data[dir_entry] = self.parse_file_data(dir_entry_path)
        elif os.path.isfile(self.zeus_path):
            self.zeus_data[self.zeus_path] = self.parse_file_data(self.zeus_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # parser.add_argument("file")
    parser.add_argument("-d", "--botnet_data", default="/extraspace/botnet-data", help="Botnet data path")
    parser.add_argument("-b", "--banklist", help="Run against a list of banks")
    parser.add_argument("-a", "--searchall", help="Run against a search term and for all data")
    parser.add_argument("-l", "--searchlist", help="Run against a list of search terms")
    parser.add_argument("-7", "--search7", help="Run against a a search term for for only the past 7 days")
    parser.add_argument("-s", "--stats", default=30, help="Number of days to run stats for. (Default 30)")
    parser.add_argument("-x", "--stats30", help="Run stats for 30 days. (Deprecated)")
    parser.add_argument("-y", "--stats72", help="Run stats for 72 days. (Deprecated)")
    parser.add_argument("-z", "--stats7", help="Run stats for 7 days. (Deprecated)")
    parser.add_argument("-w", "--hs30", help="To run historic stats for 30 days --hs30 day.month.year")
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="Print verbose debug output")
    args = parser.parse_args()

    zs = ZeusSearch(args.botnet_data)

    # report = zs.parse_file_data(args.file)

    zs.init_zeus_data()

    # # Search through Source lines
    # if args.banklist or args.searchlist or args.searchall or args.search7:
    #     timespan = 7 if args.search7 else None
    #     searchlist = []
    #     filename = None
    #
    #     if args.banklist: filename = args.banklist
    #     if args.searchlist: filename = args.searchlist
    #
    #     if filename:
    #         with open(filename) as f:
    #             searchlist = [term.strip() for term in f]
    #
    #     if args.searchall: searchlist.append(args.searchall)
    #     if args.search7: searchlist.append(args.search7)
    #
    #     search_results = zs.search_source_lines(searchlist, timespan=timespan)
    #
    #     print search_results
