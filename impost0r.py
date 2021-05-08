#!/usr/bin/env python3
"""
impost0r.py lets you clone another user's GitHub contribution calender

This is achieved by creating a repository containing backdated
commits that replicates the activity of the source user
as closely as possible.
"""

# Copyright (c) 2021 tick <tickelton@gmail.com>
# SPDX-License-Identifier:	ISC

import argparse
import tempfile
import logging
import sys
import time
import calendar
import urllib.request
import os
import re
from getpass import getpass
from typing import Dict, List
from dulwich import porcelain # type: ignore


# constants
PROGNAME = 'impost0r.py'
VERSION = '0.1.2'
SECONDS_9AM = 9 * 60 * 60
SLEEP_BETWEEN_PUSHES = 10 # Number of seconds to wait between pushes
COMMITS_PER_PUSH = 960 # Maximum number of commits per push
COMMITS_PER_PROGRESS_BAR_UPDATE = 60


# logging configuration
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.ERROR)


# global variables
branch_name = 'main'


# The progress bar function is
# Copyright (c) 2016 Vladimir Ignatev
# Licensed under the MIT License (MIT)
# SPDX-License-Identifier:	MIT
# For details see LICENSE.MIT and
# https://gist.github.com/vladignatyev/06860ec2040cb497f0f3
def progress(count: int, total: int, status: str = '') -> None:
    """Print a pretty progress bar on the console"""

    bar_len = 30
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar_string = '#' * filled_len + ' ' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s %s\r' % (bar_string, percents, '%', status))
    sys.stdout.flush()


def get_years_of_activity(user: str) -> List[bytes]:
    """Gets the years of activity from a GitHub user's profile page"""

    overview_url = 'https://github.com/' + user
    logger.info('overview_url=%s', overview_url)

    years: List[bytes] = []
    overview_page = urllib.request.urlopen(overview_url)
    overview = overview_page.readlines()
    logger.debug('overview=%s', overview)

    for line in overview:
        match = re.search(rb'id="year-link-(\d{4})', line)

        if not match:
            continue
        years.append(match.group(1))

    return years


def get_contribution_data(user: str, years: List[bytes]) -> Dict[str, int]:
    """Gets the daily acitivity from a GitHub user's contribution calendar"""

    contributions_url = 'https://github.com/users/' + user + '/contributions'
    logger.info('getting data for %s', user)
    logger.info('contributions_url=%s', contributions_url)

    contribution_data: Dict[str, int] = {}
    for year in years:
        contributions_page = urllib.request.urlopen(
            contributions_url + '?to=' + year.decode() + '-12-31')
        contributions = contributions_page.readlines()
        logger.debug('year=%s, contributions=%s', year, contributions)
        for line in contributions:
            match = re.search(rb'data-count="(\d+)".*data-date="(\d+-\d+-\d+)"', line)

            if not match:
                continue
            if match.group(1) != b'0':
                logger.debug("date=%s count=%s", match.group(2), match.group(1))
                contribution_data[match.group(2).decode()] = int(match.group(1))

    logger.debug('contribution_data=%s', contribution_data)
    return contribution_data


def diff_contribution_data(data_user: Dict[str, int], data_donor: Dict[str, int]) -> Dict[str, int]:
    """Calculates the difference between two GitHub users' activity data"""

    data_diff = {}

    for cdate in data_donor.keys():
        count_user = data_user.get(cdate, 0)
        count_donor = data_donor.get(cdate, 0)
        if count_user >= count_donor:
            continue
        data_diff[cdate] = count_donor - count_user

    logger.debug('data_diff=%s', data_diff)
    # TODO(possibly): add scaling
    #  If the user calendar has days with more commits than the
    #  donor calendar the merged calendar will look very different
    #  to the donor calendar.
    #  BEWARE: When scaling the data take care not to introduce
    #    runaway upscaling effects when the function is called
    #    repeatedly to update the user calendar when there are
    #    new contributions in the donor calendar.

    # Sorting the data is not strictly necessary but
    # by doing so the commits will also appear in
    # proper chronological order if the resulting
    # repository is viewed with e.g. 'git log'.
    # Otherwise git would show them in whatever
    # order we parsed them from the website which
    # just looks weird to a human observer.
    return dict(sorted(data_diff.items(), key=lambda item: item[0]))


def cli_get_configuration() -> Dict[str, str]:
    """Read configuration from the command line"""

    config: Dict[str, str] = {}

    config['username'] = input('Your GitHub username: ')
    if not config['username']:
        logger.error('Username required')
        sys.exit(1)
    config['email'] = input('Your GitHub email address: ')
    if not config['email']:
        logger.error('Email address required')
        sys.exit(1)
    config['password'] = getpass('Your GitHub access token: ')
    if not config['password']:
        logger.error('Access token required')
        sys.exit(1)
    config['repo'] = input('GitHub repository to create commits in: ')
    if not config['repo']:
        logger.error('Repository name required')
        sys.exit(1)
    config['donor'] = input('GitHub user to clone: ')
    if not config['donor']:
        logger.error('Donor username required')
        sys.exit(1)
    config['data_file'] = 'data.py'

    logger.info('username=%s email=%s repo=%s donor=%s data_file=%s',
                config['username'],
                config['email'],
                config['repo'],
                config['donor'],
                config['data_file'])
    return config


def do_push(repo_tmpdir, push_url, err_stream) -> None:
    """Perform the actual push"""

    global branch_name
    try:
        porcelain.push(
            repo_tmpdir,
            push_url,
            branch_name,
            outstream=err_stream,
            errstream=err_stream)
    except KeyError:
        # Github renamed the default branch for newly created
        # repositories from 'master' to 'main'. To support
        # both new and legacy repos, we first try 'main' and
        # if that fails we use 'master' instead.
        branch_name = 'master'
        porcelain.push(
            repo_tmpdir,
            push_url,
            branch_name,
            outstream=err_stream,
            errstream=err_stream)

def main() -> None:
    """impost0r.py main function"""

    parser = argparse.ArgumentParser(prog=PROGNAME)
    parser.add_argument('--verbose', '-v', action='count', default=0)
    parser.add_argument('--version', action='version', version='%(prog)s v' + VERSION)
    args = parser.parse_args()
    if args.verbose == 1:
        logger.setLevel(logging.WARNING)
    elif args.verbose == 2:
        logger.setLevel(logging.INFO)
    elif args.verbose > 2:
        logger.setLevel(logging.DEBUG)

    config: Dict[str, str] = cli_get_configuration()

    tempdir = tempfile.TemporaryDirectory()
    logger.info('Using tempdir=%s', tempdir.name)

    repo_url = 'https://github.com/' +  config['username'] + '/' + config['repo']
    repo_tmpdir = tempdir.name + '/' + config['repo']
    repo_data_file = repo_tmpdir + '/' + config['data_file']
    push_url = 'https://'\
            + config['username']\
            + ':'\
            + config['password']\
            + '@github.com/'\
            + config['username']\
            + '/'\
            + config['repo']
    logger.info('Cloning %s to %s', repo_url, repo_tmpdir)

    active_years: List[bytes] = get_years_of_activity(config['donor'])
    if not active_years:
        logger.error('No yearly data found for %s.', config['donor'])
        sys.exit(0)

    # NOTE: There seems to be a weird caching issue here.
    #       Sometimes newly created commits in the user
    #       repo are not visible for days in the list
    #       of years of activity on the overview page
    #       which leads to unnecessary commits being
    #       created on consecutive runs.
    #       Therefore we only get the years of activity
    #       of the donor user and use those also to
    #       get activity data for the target user.
    #       Otherwise running impost0r
    #       in quick succession with the same
    #       configuration can have unintended
    #       consequences and create freakishly
    #       large repositories.
    print('Getting activity for {}...'.format(config['username']))
    data_user: Dict[str, int] = get_contribution_data(config['username'], active_years)
    print('Getting activity for {}...'.format(config['donor']))
    data_donor: Dict[str, int] = get_contribution_data(config['donor'], active_years)
    if not data_donor:
        print('No activity found for {}.'.format(config['donor']))
        sys.exit(0)

    print('Calculating commit data...')
    data_repo = diff_contribution_data(data_user, data_donor)
    if not data_repo:
        print('{} does not seem to have more contributions than {}.'.format(
            config['donor'],
            config['username']
            ))
        print('Nothing to do; exiting.')
        sys.exit(0)

    author_data = config['username'].encode()\
            + ' <'.encode()\
            + config['email'].encode()\
            + '>'.encode()
    logger.info('Using author data: \'%s\'', author_data.decode())

    print('Cloning {}...'.format(repo_url))
    devnull = open(os.devnull, 'w')
    err_stream = getattr(devnull, 'buffer', None)
    repo = porcelain.clone(repo_url, repo_tmpdir, errstream=err_stream)

    print('Creating and pushing new commits ...')
    # NOTE: GitHub will not correctly update the
    #       calendar if a repository with more than 1000
    #       new commits is pushed. Only the most recent
    #       1000 will be displayed in the calendar.
    #       Workaround: create and push commits in
    #       several turns. And wait a couple of seconds
    #       between pushes to let GitHub do its magic.
    total_commit_count = sum(data_repo.values())
    commits_generated = 0
    for (commit_date, commit_count) in data_repo.items():
        for commit_num in range(0, commit_count):
            commit_stamp = calendar.timegm(
                time.strptime(commit_date, '%Y-%m-%d')) + commit_num + SECONDS_9AM
            data_file = open(repo_data_file, 'w')
            data_file.write(commit_date + str(commit_num))
            data_file.close()
            porcelain.add(repo, repo_data_file)
            commits_generated += 1
            repo.do_commit(
                message=commit_date.encode(),
                committer=author_data,
                author=author_data,
                commit_timestamp=commit_stamp)

            if not commits_generated % COMMITS_PER_PROGRESS_BAR_UPDATE:
                progress(commits_generated, total_commit_count)

            if not commits_generated % COMMITS_PER_PUSH:
                logger.info('pushing...')
                do_push(repo_tmpdir, push_url, err_stream)
                # NOTE: A certain minimum wait between pushes seems
                #       to be necessary. Otherwise the activity data
                #       in the calendar will be displayed correctly
                #       but the list of years of activity will not
                #       be updated!
                time.sleep(SLEEP_BETWEEN_PUSHES)

    if commits_generated % COMMITS_PER_PUSH:
        logger.info('final push')
        progress(commits_generated, total_commit_count)
        do_push(repo_tmpdir, push_url, err_stream)

    progress(commits_generated, total_commit_count)
    print('\nFinished')

    repo.close()

    tempdir.cleanup()


if __name__ == '__main__':
    main()
