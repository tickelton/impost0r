#!/usr/bin/env python3

import argparse
import tempfile
import logging
import sys
import time
import calendar
import dulwich
import urllib.request
import re
from dulwich import porcelain
from getpass import getpass

# constants
seconds_9AM = 9 * 60 * 60

# logging configuration
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
                '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.ERROR)


# The progress bar function is
# Copyright (c) 2016 Vladimir Ignatev
# Licensed under the MIT License (MIT)
# For details see LICENSE.MIT and
# https://gist.github.com/vladignatyev/06860ec2040cb497f0f3
def progress(count, total, status=''):
    bar_len = 30
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '#' * filled_len + ' ' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s %s\r' % (bar, percents, '%', status))
    sys.stdout.flush()

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
    # TODO: There seems to be a weird caching issue here.
    #       sometimes newly created commits in the user
    #       repo are not seen for days which leads to
    #       unnecessary commits being created on
    #       consecutive runs.
    #       Maybe it would be better to get the years of
    #       activity for both users beforehand and
    #       use the longer period of the two for
    #       both users ?
    # WARNING: For the same reason running impost0r
    #       in quick succession with the same
    #       configuration can have unintended
    #       consequences and create freakishly
    #       large repositories.
    #       Since there is no good way to properly
    #       handle this without knowing the
    #       user's intention that should be mentioned
    #       in the documentation !
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

    for cdate in data_donor.keys():
        count_user = data_user.get(cdate, 0)
        count_donor = data_donor.get(cdate, 0)
        if count_user >= count_donor:
            continue
        data_diff[cdate] = count_donor - count_user

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


def cli_get_configuration():
    config = {}

    config['username'] = input('Your Github username: ')
    config['email'] = input('Your Github email address: ')
    config['password'] = getpass('Your Github password: ')
    config['repo'] = input('Github repository to create commits in: ')
    config['donor'] = input('Github user to clone: ')
    config['data_file'] = 'data.py'

    # TODO: Do some sanity checking of configuration
    return config


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count', default=0)
    args = parser.parse_args()
    if args.verbose == 1:
        logger.setLevel(logging.WARNING)
    elif args.verbose == 2:
        logger.setLevel(logging.INFO)
    elif args.verbose > 2:
        logger.setLevel(logging.DEBUG)

    config = cli_get_configuration()

    tempdir = tempfile.TemporaryDirectory()
    logger.debug('Using tempdir=%s', tempdir.name)

    repo_url = 'https://github.com/' +  config['username'] + '/' + config['repo']
    repo_tmpdir = tempdir.name + '/' + config['repo']
    repo_data_file = repo_tmpdir + '/' + config['data_file']
    push_url = 'https://' + config['username'] + ':' + config['password'] + '@github.com/' + config['username'] + '/' + config['repo']
    logger.debug('Cloning %s to %s', repo_url, repo_tmpdir)

    data_user = get_contribution_data(config['username'])
    data_donor = get_contribution_data(config['donor'])
    data_repo = diff_contribution_data(data_user, data_donor)

    author_data = config['username'].encode() + ' <'.encode() + config['email'].encode() + '>'.encode()
    repo = porcelain.clone(repo_url, repo_tmpdir)

    # NOTE: Github will not correctly update the
    #       calendar if a repository with more than 1000
    #       new commits is pushed. Only the most recent
    #       1000 will be displayed in the calendar.
    #       Workaround: create and push commits in
    #       several turns. And wait a couple of seconds
    #       between pushes to let Github do its magic.
    commits_generated = 0
    for commit_date in data_repo.keys():
        for commit_num in range(0, data_repo[commit_date]):
            commit_stamp = calendar.timegm(time.strptime(commit_date, '%Y-%m-%d')) + commit_num + seconds_9AM
            f = open(repo_data_file, 'w')
            f.write(commit_date + str(commit_num))
            f.close()
            porcelain.add(repo, repo_data_file)
            commits_generated += 1
            repo.do_commit(message=commit_date.encode(), committer=author_data, author=author_data, commit_timestamp=commit_stamp)

            if not commits_generated % 60:
                # TODO: Compute expected total commits beforehand
                #       and display a progress bar ?
                pass

            if commits_generated == 960:
                logger.info('pushing...')
                r2 = porcelain.push(repo_tmpdir, push_url, 'master')
                # TODO: The sleep should not be necessary as
                #       repo creation is sufficiently slow to
                #       not confuse Github with too many commits.
                #       can this be made more robust ?
                #time.sleep(10)
                commits_generated = 0

    if commits_generated:
        logger.info('final push')
        r2 = porcelain.push(repo_tmpdir, push_url, 'master')

    repo.close()
    
    tempdir.cleanup()


if __name__ == '__main__':
    main()

