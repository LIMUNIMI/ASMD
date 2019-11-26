#! /usr/bin/env python3

import json
import os
import pathlib
from getpass import getpass
from ftplib import FTP
from urllib.request import urlretrieve, urlcleanup
from urllib.parse import urlparse
from collections import deque
from shutil import unpack_archive
import readline
readline.parse_and_bind("tab: complete")

#: Set to True to skip datasets which already exist
SKIP_EXISTING_DIR = True

supported_archives = {
    '.zip': 'zip',
    '.tar': 'tar',
    '.tar.gz': 'gztar',
    '.tar.bz': 'bztar',
    '.tar.xz': 'xztar'
}

def chose_dataset(data, install_dir):
    """
    Ask for preferred datasets and removes unwanted from data. Also skips
    dataset with existing directories.
    """
    print("Please, insert the number relative to the datasets that you want to download (ex. 1, 2, 3, 11, 2):")
    for i, d in enumerate(data):
        print(i, "-", d['name'])

    flag = False
    while not flag:
        try:
            answer = input("Which datasets do you want? ")
            # apply `int` function to each element in answer (characters) and convert to list
            datalist = list(map(int, answer.split(', ')))
            flag = True
        except ValueError:
            print("Wrong answer, please use only numbers in your answer.")
            flag = False

    print()
    # skipping directories already existing
    i = 0
    for k in range(len(data)):
        d = data[i]
        SKIP = os.path.isdir(os.path.join(install_dir, d['name'])) and SKIP_EXISTING_DIR
        if (SKIP) or (k not in datalist):
            print('Skipping ' + d['name'] + ": already exists, or not selected!")
            del data[i]
            i -= 1
        i += 1


def ftp_download(d, credential, install_dir, parsed_url=None):
    """
    NO MORE USED
    download all files at d['url'] using user and password in `credentials`
    """
    if parsed_url is None:
        parsed_url = urlparse(d['url'])
    os.makedirs(os.path.join(install_dir, d['name']), exist_ok=True)
    downloaded_files = []

    # ftp
    with FTP(parsed_url.netloc) as ftp:
        ftp.login(user=credential['user'], passwd=credential['passwd'])
        ftp.cwd(parsed_url.path)
        filenames = ftp.nlst()  # get filenames within the directory

        for filename in filenames:
            local_filename = os.path.join(install_dir, d['name'], filename)
            file = open(local_filename, 'wb')
            ftp.retrbinary('RETR ' + filename, file.write)
            if local_filename.endswith('.zip'):
                downloaded_files.append(local_filename)

    return downloaded_files


def get_credentials(data):
    """
    NO MORE USED
    """
    credentials = [d['name'] for d in data if d['login']]
    for i, credential in enumerate(credentials):
        print("================")
        print("Login credentials for " + credential)
        user = input("User: ")
        password = getpass("Password: ")
        credentials[i] = {"user": user, "passwd": password}

    print("================")
    print()
    return credentials


def intro(data):
    print("Starting installation")
    print("---------------------")
    print("Author: " + data['author'])
    print("Year: ", data['year'])
    print("------------------")
    print()


def download(item, credentials, install_dir):
    """
    Really download the files. Credentials (from login) are supported only for
    FTP connections for now.
    """
    # getting credential credentials
    if item['login']:
        credential = credentials.popleft()

    # getting the protocol and the resource to be downloaded
    parsed_url = urlparse(item['url'])
    if parsed_url.scheme == 'ftp':
        # FTP
        # at now, no FTP connection is needed
        downloaded_file = ftp_download(item, credential, install_dir, parsed_url)
    else:
        # http, https
        temp_fn, _header = urlretrieve(
            item['url'],
            filename=os.path.join(install_dir, 'temp')
        )
        downloaded_file = [temp_fn]
    return downloaded_file


def main():

    with open('datasets.json') as f:
        json_file = json.load(f)

    default_dir = json_file['install_dir'] or './'
    install_dir = input("Path to install datasets [empty to default "+ default_dir + "] ")
    if not install_dir:
        install_dir = default_dir
    json_file['install_dir'] = install_dir

    intro(json_file)

    data = json_file['datasets']
    chose_dataset(data, install_dir)

    # at now, no credential is needed
    credentials = deque(get_credentials(data))
    for d in data:
        full_path = os.path.join(install_dir, d['name'])
        print("Creating " + d['name'])

        if d['url'] != 'unknown':
            downloaded_file = download(d, credentials, install_dir)

        # unzipping if needed
        if d['unpack']:
            for temp_fn in downloaded_file:
                format =  ''.join(pathlib.Path(d['url']).suffixes) or '.zip'
                format = [j for i, j in supported_archives.items() if format.endswith(i)][0]
                unpack_archive(temp_fn, full_path, format)
                # cleaning up
                os.remove(temp_fn)

        # post-processing
        if d['post-process'] != 'unknown':
            # recursively concatenate commands
            command = '; '.join(list(map(lambda x: ''.join(x), d['post-process'])))
            command = command.replace('&install_dir', json_file['install_dir'])
            os.system(command)
        print("------------------")

        # just to be sure
        urlcleanup()

    gt_archive_fn = 'ground_truth.tar.xz'
    if os.path.exists(gt_archive_fn):
        # unpacking the ground_truth data
        unpack_archive(gt_archive_fn, install_dir, 'xztar')

    # saving the Json file as modified
    # not using json.dump beacuse it uses ugly syntax
    with open('datasets.json', 'r+') as fd:
        contents = fd.readlines()
        fd.seek(0)
        fd.writelines(contents)


if __name__ == '__main__':
    main()
