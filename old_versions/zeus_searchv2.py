#!/usr/bin/python

import os
import os.path
import collections
import tldextract
from datetime import datetime, timedelta
from sys import argv

lineNum = 0
startstr = False
thisbank = None
thisterm = None
included_date = True
cur_buff = []
banklist = []
bankdata = {}
path = r'./botnet-data-large'
data = {}
mytime = datetime.now().strftime("%d.%m.%Y")
cur_time = datetime.now()
timeframe = 7
timeset = datetime.now() - timedelta(days=7)
inputType = argv[1]


def optionfile():
    global lineNum
    global startstr
    global cur_buff
    global bankdata
    global thisbank
    global banklist
    global included_date

    dirread()
    for entry in data.iterkeys():
        for line in data[entry]:
            if line.startswith('========'):
                if len(cur_buff) > 0 and thisbank is not None and included_date:
                    try:
                        bankdata[thisbank]
                    except:
                        bankdata[thisbank] = list()
                    bankdata[thisbank].append(cur_buff)
                startstr = True
                thisbank = None
                included_date = True
                cur_buff = list()
            elif startstr and line.startswith('Bot ID:'):
                startstr = False
            elif inputType == '--banklist' and startstr and line.startswith('Report time:'):
                try:
                    report_time = datetime.strptime(' '.join(line.split(' ')[-2:]), "%d.%m.%Y %H:%M:%S")
                    time_diff = cur_time - report_time
                    if time_diff.days > timeframe:
                        included_date = False
                    else:
                        cur_buff.append(line)
                except:
                    print "invalid date format:"
                    print line
            elif startstr:
                if line.startswith('Source:'):
                    for banks in banklist:
                        if banks in line:
                            thisbank = banks
                cur_buff.append(line)
            lineNum += 1

    for bank in bankdata.iterkeys():
        bankstuff = (mytime + '_' + bank + '.txt')
        bankfile = os.path.join(bank, bankstuff)
        if not os.path.exists(bank):
            os.makedirs(bank)
        outfile = open(bankfile, 'w')
        for bot in bankdata[bank]:
            for request in bot:
                outfile.write(request + '\n')
            outfile.write('=========================================================\n')
        outfile.close()


def optionterm():
    global lineNum
    global startstr
    global cur_buff
    global included_date
    global thisterm
    term = argv[2]
    termdata = {}

    dirread()
    for entry in data.iterkeys():
        for line in data[entry]:
            if line.startswith('========'):
                if len(cur_buff) > 0 and thisterm is not None and included_date:
                    try:
                        termdata[thisterm]
                    except:
                        termdata[thisterm] = list()
                    termdata[thisterm].append(cur_buff)
                startstr = True
                thisterm = None
                included_date = True
                cur_buff = list()
            elif startstr and line.startswith('Bot ID:'):
                startstr = False
            elif inputType == '--search7' and startstr and line.startswith('Report time:'):
                try:
                    report_time = datetime.strptime(' '.join(line.split(' ')[-2:]), "%d.%m.%Y %H:%M:%S")
                    time_diff = cur_time - report_time
                    if time_diff.days > timeframe:
                        included_date = False
                    else:
                        cur_buff.append(line)
                except:
                    print "invalid date format:"
                    print line
            elif startstr:
                if line.startswith('Source:'):
                    if term in line:
                        thisterm = term
                cur_buff.append(line)
            lineNum += 1

    for shizzle in termdata.iterkeys():
        termfile = (mytime + '_' + term + '.txt')
        termdir = os.path.join(term, termfile)
        if not os.path.exists(term):
            os.makedirs(term)
        outfile = open(termdir, 'w')
        for bot in termdata[shizzle]:
            for request in bot:
                outfile.write(request + '\n')
            outfile.write('=========================================================\n')
        outfile.close()

def optionstats():
    global lineNum
    global startstr
    global included_date
    timeframe72 = 3
    timeframe30days = 30
    timeframe7day = 7
    statsdata = {}
    thisbot = None
    email_buff = []
    bots_buff = []
    topdoms_buff = []
    IP_buff = []

    dirread()
    for entry in data.iterkeys():
        for line in data[entry]:
            if line.startswith('========'):
                if len(bots_buff) > 0 and thisbot is not None and included_date:
                    try:
                        statsdata[thisbot]
                    except:
                        statsdata[thisbot] = list()
                    statsdata[thisbot].append(bots_buff)
                startstr = True
                thisbot = None
                included_date = False
                bots_buff = list()
            elif line.startswith('Bot ID:'):
                startstr = True
                bots_buff.append(line)
                thisbot = line
            elif inputType == '--stats72' and startstr and line.startswith('Report time:'):
                try:
                    report_time = datetime.strptime(' '.join(line.split(' ')[-2:]), "%d.%m.%Y %H:%M:%S")
                    time_diff = cur_time - report_time
                    if time_diff.days > timeframe72:
                        included_date = False
                    else:
                        included_date = True
                except:
                    print "invalid date format:"
                    print line
            elif inputType == '--stats30' and startstr and line.startswith('Report time:'):
                try:
                    report_time = datetime.strptime(' '.join(line.split(' ')[-2:]), "%d.%m.%Y %H:%M:%S")
                    time_diff = cur_time - report_time
                    if time_diff.days > timeframe30days:
                        included_date = False
                    else:
                        included_date = True
                except:
                    print "invalid date format:"
                    print line
            elif inputType == '--hs30' and startstr and line.startswith('Report time:'):
                mydate = argv[2]
#                sucks = datetime.strptime(mydate,"%d.%m.%Y %H:%M:%S")
                sucks = datetime.strptime(mydate,"%d.%m.%Y")
                try:
                    report_time = datetime.strptime(' '.join(line.split(' ')[-2:]), "%d.%m.%Y %H:%M:%S")
                    time_diff = sucks - report_time
                    if time_diff.days > timeframe30days or time_diff.days < 0:
                        included_date = False
                    else:
                        included_date = True
                except:
                    print "invalid date format:"
                    print line
            elif inputType == '--stats7' and startstr and line.startswith('Report time:'):
                try:
                    report_time = datetime.strptime(' '.join(line.split(' ')[-2:]), "%d.%m.%Y %H:%M:%S")
                    time_diff = cur_time - report_time
                    if time_diff.days > timeframe7day:
                        included_date = False
                    else:
                        included_date = True
                except:
                    print "invalid date format:"
                    print line
            elif startstr:
                if line.startswith('pop3:') and included_date:
                    email_buff.append(line)
                if line.startswith('IPv4:') and included_date:
                    IP_buff.append(line)
                elif line.startswith('Source:                       http') and included_date:
                    #topdoms_buff.append(line)
                    entry = line[31:]
                    try:
                        url = tldextract.extract(entry)
                        if url.subdomain:
                            fullurl = '.'.join(url[:3])
                            topdoms_buff.append(fullurl)
                        elif url.domain and url.suffix:
                            fullurl = url.domain+'.'+url.suffix
                            topdoms_buff.append(fullurl)
                        else:
                            fullurl = url.domain
                            topdoms_buff.append(fullurl)
                    except:
                        print line
            lineNum += 1

    if not os.path.exists('stats'):
        os.makedirs('stats')
    botsset = set(statsdata)
    emailset = set(email_buff)
    domcount=collections.Counter(topdoms_buff)
    IPset = set(IP_buff)
    botcount = len(botsset)
    emailcount = len(emailset)
    IPcount = len(IPset)
    if inputType == '--stats30':
            botstatsfile = (mytime + '_' + 'botidstats30day' + '.txt')
            emailstatsfile = (mytime + '_' + 'emailstats30day' + '.txt')
            topdomsfile = (mytime + '_' + 'topdoms30day' + '.txt')
            IPfile = (mytime + '_' + 'IP30day' + '.txt')
            sumfile = (mytime + '_' + '30daysummary' + '.txt')
    if inputType == '--hs30':
            mydate = argv[2]
            botstatsfile = (mydate + '_' + 'botidstats' + '.txt')
            emailstatsfile = (mydate + '_' + 'emailstats' + '.txt')
            topdomsfile = (mydate + '_' + 'topdoms' + '.txt')
            IPfile = (mydate + '_' + 'IP' + '.txt')
            sumfile = (mydate + '_' + 'summary' + '.txt')
    elif inputType == '--stats72':
            botstatsfile = (mytime + '_' + 'botidstats3day' + '.txt')
            emailstatsfile = (mytime + '_' + 'emailstats3day' + '.txt')
            topdomsfile = (mytime + '_' + 'topdoms3day' + '.txt')
            IPfile = (mytime + '_' + 'IP3day' + '.txt')
            sumfile = (mytime + '_' + '3daysummary' + '.txt')
    elif inputType == '--stats7':
            botstatsfile = (mytime + '_' + 'botidstats7day' + '.txt')
            emailstatsfile = (mytime + '_' + 'emailstats7day' + '.txt')
            topdomsfile = (mytime + '_' + 'topdoms7day' + '.txt')
            IPfile = (mytime + '_' + 'IP7day' + '.txt')
            sumfile = (mytime + '_' + '7daysummary' + '.txt')
    botstatsdir = os.path.join('stats', botstatsfile)
    emailstatsdir = os.path.join('stats', emailstatsfile)
    topdomsdir = os.path.join('stats', topdomsfile)
    IPdir = os.path.join('stats', IPfile)
    sumdir = os.path.join('stats', sumfile)
    outfile = open(botstatsdir, 'w')
    outfile2 = open(emailstatsdir, 'w')
    outfile3 = open(topdomsdir, 'w')
    outfile4 = open(IPdir, 'w')
    outfile5 = open(sumdir, 'w')
    for shizzle in botsset:
        outfile.write(shizzle + '\n')
    outfile.close()
    for pop3 in emailset:
		outfile2.write(pop3 + '\n')
    outfile2.close()
#    for domain, count in domcount.most_common(10):
#        outfile3.write('\n'.join('{}: {}'.format(domain, count))
    outfile3.write('\n'.join('{}: {}'.format(dom,count) for dom,count in domcount.most_common(100)))
    outfile3.close()
    for IP in IPset:
        outfile4.write(IP + '\n')
    outfile4.close()
    if inputType == '--stats30':
        outfile5.write('This is the 30day summary' + '\n' + 'Bots: ' + str(botcount) + '\n' + 'Email accounts: ' + str(emailcount) + '\n' + 'Bot IPs: ' + str(IPcount) + '\n')
    elif inputType == '--hs30':
        mydate = argv[2]
        outfile5.write('This is the monthly summary for '+ mydate + '\n' + 'Bots: ' + str(botcount) + '\n' + 'Email accounts: ' + str(emailcount) + '\n' + 'Bot IPs: ' + str(IPcount) + '\n')
    elif inputType == '--stats72':
        outfile5.write('This is the 3day summary' + '\n' + 'Bots: ' + str(botcount) + '\n' + 'Email accounts: ' + str(emailcount) + '\n' + 'Bot IPs: ' + str(IPcount) + '\n')
    elif inputType == '--stats7':
        outfile5.write('This is the 7day summary' + '\n' + 'Bots: ' + str(botcount) + '\n' + 'Email accounts: ' + str(emailcount) + '\n' + 'Bot IPs: ' + str(IPcount) + '\n')

def dirread():
    for dir_entry in os.listdir(path):
        dir_entry_path = os.path.join(path, dir_entry)
        if os.path.isfile(dir_entry_path):
            with open(dir_entry_path, 'r') as my_file:
                data[dir_entry] = my_file.read().splitlines()

if inputType == '--banklist' or inputType == '--searchlist':
    mybanks = open(argv[2], 'r')
    for banksinline in mybanks:
        banksinline = banksinline.strip()
        banklist.append(banksinline)
    optionfile()
elif inputType == '--searchall' or inputType == '--search7':
    optionterm()
elif inputType == '--stats72' or inputType == '--stats30' or inputType == '--stats7' or inputType == '--hs30':
    optionstats()
elif inputType == '--help':
    print 'To run the script against a list of banks you will type  --banklist banklist'
    print 'To run the script against a search term and for all data you will type --searchall searchterm'
    print 'To run the script against a search term and for only the past 7 days you will type --search7 searchterm'
    print 'To run the script against a list of search terms you will type  --searchlist yourlist'
    print 'To run stats for 30 days  --stats30'
    print 'To run stats for 3 days  --stats72'
    print 'To run stats for 7 days  --stats7'
    print 'To run historic stats for 30 days  --hs30 day.month.year'
