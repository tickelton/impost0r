#!/usr/bin/env python3

import tempfile
import logging
import sys
import time
import dulwich
import urllib.request
import re
from dulwich import porcelain

# global variables
user_name = 'XXXX'
user_pass = 'YYYY'
repo_name = 'impost0r-demo'
data_file = 'data.py'
user_email = 'tickelton@gmail.com'
donor_name = 'ZZZZ'


# logging configuration
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
                '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def get_contribution_data(user):
    contributions_url = 'https://github.com/users/' + user + '/contributions'
    overview_url = 'https://github.com/' + user
    logger.info('getting data for %s', user)
    logger.debug('contributions=%s overview=%s', contributions_url, overview_url)

    years = []
    overview_page = urllib.request.urlopen(overview_url)
    overview = overview_page.readlines()

    for line in overview:
        match = re.search(b'id="year-link-(\d{4})', line)

        if not match:
            continue
        years.append(match.group(1))

    contribution_data = {}
    for year in years:
        contributions_page = urllib.request.urlopen(contributions_url + '?to=' + year.decode() + '-12-31')
        contributions = contributions_page.readlines()
        for line in contributions:
            match = re.search(br'data-count="(\d+)".*data-date="(\d+-\d+-\d+)"', line)

            if not match:
                continue
            if match.group(1) != b'0':
                #print("date={} count={}".format(match.group(2), match.group(1)))
                contribution_data[match.group(2).decode()] = int(match.group(1))

    return contribution_data

def diff_contribution_data(data_user, data_donor):
    data_diff = {}
    #print(data_donor)
    #print(data_user)

    for cdate in data_donor.keys():
        count_user = data_user.get(cdate, 0)
        count_donor = data_donor.get(cdate, 0)
        if count_user >= count_donor:
            continue
        data_diff[cdate] = count_donor - count_user

    #print(data_diff)
    # TODO(possibly): add scaling
    #  if the user calendar has days with more commits than the
    #  donor calendar the merged calendar will look very different
    #  to the donor calendar.
    #  BEWARE: when scaling the data take care not to introduce
    #    runaway upscaling effects when the function is called
    #    repeatedly to update the user calendar when there are
    #    new contributions in the donor calendar.
    return dict(sorted(data_diff.items(), key=lambda item: item[0]))


def main():

    tempdir = tempfile.TemporaryDirectory()
    logger.debug('Using tempdir=%s', tempdir.name)

    repo_url = 'https://github.com/' +  user_name + '/' + repo_name
    repo_tmpdir = tempdir.name + '/' + repo_name
    repo_data_file = repo_tmpdir + '/' + data_file
    logger.debug('Cloning %s to %s', repo_url, repo_tmpdir)

    data_user = get_contribution_data(user_name)
    data_donor = get_contribution_data(donor_name)
    data_repo = diff_contribution_data(data_user, data_donor)

    author_data = user_name.encode() + ' <'.encode() + user_email.encode() + '>'.encode()
    repo = porcelain.clone(repo_url, repo_tmpdir)

    # TODO: currently only creates on commit per day
    #       needs to use data_repo[commit_date] 
    # TODO: github will not correctly update the
    #       calendar if a repository with commits for
    #       more than ~4 years is pushed.
    #       Workaround: create and push commits in
    #       several turns (yearly?) and wait some
    #       time between pushes (1 minute should work).
    for commit_date in data_repo.keys():
        commit_stamp = time.mktime(time.strptime(commit_date, '%Y-%m-%d')) + 37334 # magic constant to set the commit time to 9:22:14 AM
        f = open(repo_data_file, 'w')
        f.write(commit_date)
        f.close()
        porcelain.add(repo, repo_data_file)
        repo.do_commit(message=commit_date.encode(), committer=author_data, author=author_data, commit_timestamp=commit_stamp)

    r2 = porcelain.push(repo_tmpdir, 'https://' + user_name + ':' + user_pass + '@github.com/' + user_name + '/' + repo_name, 'master')
    repo.close()
    
    tempdir.cleanup()


if __name__ == '__main__':
    main()

