#!/usr/bin/env python3

import re
import urllib.request

contributions_url = 'https://github.com/users/tickelton/contributions?to=2019-12-31'
overview_url = 'https://github.com/tickelton'

contributions_page = urllib.request.urlopen(contributions_url)
contributions = contributions_page.readlines()

overview_page = urllib.request.urlopen(overview_url)
overview = overview_page.readlines()

for line in overview:
    match = re.search(b'id="year-link-(\d{4})', line)

    if not match:
        continue
    print(match.group(1))

for line in contributions:
    match = re.search(br'data-count="(\d+)".*data-date="(\d+-\d+-\d+)"', line)

    if not match:
        continue
    print("date={} count={}".format(match.group(2), match.group(1)))


