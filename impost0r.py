#!/usr/bin/env python3

import tempfile
import logging
import sys
import time
import pygit2

# global variables
repo_name = 'decoy'


# logging configuration
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
                '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def get_user_data():
    "Get name and email address for commit from global git config"

    ret_name = ''
    ret_addr = ''

    c = pygit2.Config.get_global_config()
    names = c.get_multivar('user.name')
    email_addrs = c.get_multivar('user.email')

    for n in names:
        if n:
            ret_name = n
    for a in email_addrs:
        if a:
            ret_addr = a

    if not ret_name:
        logger.warning('Unable to determine username from global git config')
    if not ret_addr:
        logger.warning('Unable to determine email address from global git config')

    logger.info('Using user=%s,email=%s', ret_name, ret_addr)
    return (ret_name, ret_addr)



def main():
    
    (user_name, user_email) = get_user_data()
    if not user_name or not user_email:
        print('TODO: ask for user/email')
        sys.exit(1)

    tempdir = tempfile.TemporaryDirectory()
    logger.debug('Using tempdir=%s', tempdir.name)

    repo_url = 'https://github.com/' +  user_name + '/' + repo_name
    repo_tmpdir = tempdir.name + '/' + repo_name + '.git'
    logger.debug('Cloning %s to %s', repo_url, repo_tmpdir)
    repo = pygit2.clone_repository(repo_url, repo_tmpdir)    
    
    #tempdir.cleanup()


if __name__ == '__main__':
    main()

