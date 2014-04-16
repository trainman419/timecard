#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import yaml
import urllib
import pdfkit
import argparse
import mechanize
import datetime
from BeautifulSoup import BeautifulSoup

def main():
    today = datetime.date.today()
    day = today.day
    if day <= 15:
        day = 1
    else:
        day = 16
    start_date = "%02d/%02d/%04d" % ( today.month, day, today.year )
    parser = argparse.ArgumentParser("Timecard login and submission")
    parser.add_argument('-c', '--config', help="Configuration file (yaml)",
            default='timecard.yaml')
    parser.add_argument('-d', '--date', help="Starting Date",
            default=start_date)
    args = parser.parse_args()

    if not os.path.isfile(args.config):
        print("ERROR: %s is not a file" % ( args.config ))
        sys.exit(1)

    config = yaml.load(open(args.config))

    start_date = args.date
    print("Getting timesheet for %s" % ( start_date ))

    b = mechanize.Browser()
    b.set_handle_robots(False)
    # timecard URL: https://axess.sahr.stanford.edu/group/guest/my-timecard-leave-balances
    login = b.open('https://axess.sahr.stanford.edu/group/guest/my-timecard-leave-balances')
    b.select_form(name='login')
    b['username'] = config['username']
    b['password'] = config['password']
    response = b.submit()
    two_factor = False
    for form in b.forms():
        if form.name == 'login':
            two_factor = True
    
    if two_factor:
        b.select_form(name='login')
        otp = raw_input("Login Token: ")
        b['otp'] = otp
        response = b.submit()

    response = b.open('https://axess.sahr.stanford.edu/psp/pscsprd/EMPLOYEE/HRMS/c/ROLE_EMPLOYEE.TL_MSS_EE_SRCH_PRD.GBL')
    target_url = None
    for l in b.links():
        for attr in l.attrs:
            if attr[0] == 'name' and attr[1] == 'TargetContent':
                target_url = l.url
    if not target_url:
        print("ERROR: target URL not found")
        sys.exit(1)

    # set DATE_DAY1: 04/16/2014 for the first day in the timecard range
    b.open(target_url)
    data=urllib.urlencode({
        'ICAJAX': 0,
        'ICAction': 'STF_TL_DERIVED_PRINT_BTN',
        'DATE_DAY1': start_date,
        'DERIVED_TL_WEEK_VIEW_BY_LIST': 'T',
        })
    request = mechanize.Request(target_url, data)
    target = b.open(request)

    orig_timesheet = target.read()

    soup = BeautifulSoup(orig_timesheet)

    images = {}

    for img in soup.findAll('img'):
        src = img['src']
        fname = os.path.basename(src)
        if not fname in images:
            print("Downloading %s to %s" % (src, fname))
            image_data = b.open(src)
            with open(fname, 'wb') as o:
                o.write(image_data.read())
        img['src'] = fname

    stylesheets = {}

    for css in soup.findAll('link'):
        src = css['href']
        fname = os.path.basename(src)
        if not fname in stylesheets:
            print("Downloading %s to %s" % (src, fname))
            style_data = b.open(src)
            with open(fname, 'wb') as o:
                o.write(style_data.read())
        css['href'] = fname

    with open('tmp.html', 'w') as o:
        o.write(str(soup))
        print("Output written to tmp.html")

    pdfname = "timesheet_%s.pdf" % ( start_date )
    pdfname = pdfname.replace('/', '-')
    pdfkit.from_file('tmp.html', pdfname)
    print("Timesheet written to %s" % (pdfname))
            

if __name__ == '__main__':
    main()
