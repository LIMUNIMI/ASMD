#! /usr/bin/env python3

from __future__ import print_function, unicode_literals
import json
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.validation import Validator
from prompt_toolkit import prompt
import os
import pathlib
import tempfile
from pyfiglet import Figlet
from alive_progress import alive_bar
from subprocess import Popen, DEVNULL
from os.path import join as joinpath
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
    print("\nPlease, insert the number relative to the datasets that you want \
to download (ex. 1, 2, 3, 11, 2). If corresponding directories already exist, \
they will be skipped. Empty to select all of them.")
    for i, d in enumerate(data):
        print(i, "-", d['name'])

    flag = False
    while not flag:
        try:
            answer = prompt("\nWhich datasets do you want? ")
            # apply `int` function to each element in answer (characters) and
            # convert to list
            if answer == '':
                answer = list(range(len(data)))
                flag = True
            else:
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
        SKIP = os.path.isdir(os.path.join(install_dir,
                                          d['name'])) and SKIP_EXISTING_DIR
        if (SKIP) or (k not in datalist):
            print('Skipping ' + d['name'] +
                  ": already exists, or not selected!")
            del data[i]
            i -= 1
        i += 1


def load_definitions():
    validator = Validator.from_callable(
        lambda x: os.path.isdir(x) or x == '',
        error_message="Not a directory!",
        move_cursor_to_end=True,
    )
    path_completer = PathCompleter(only_directories=True)
    question = "\nType the path to a definition dir (empty to continue) "

    print("\n------------------")
    datasets = []
    path = prompt(question, completer=path_completer, validator=validator)
    while path != "":
        # look for json files in path
        for file in os.listdir(path):
            fullpath = joinpath(path, file)
            if os.path.isfile(fullpath) and fullpath.endswith('.json'):
                # add this dataset
                datasets.append(json.load(open(fullpath, 'rt')))
        path = prompt(question, completer=path_completer, validator=validator)
    return datasets


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
        print("Login credentials for " + credential)
        user = input("User: ")
        password = getpass("Password: ")
        credentials[i] = {"user": user, "passwd": password}

    print()
    return credentials


def intro(data):
    f = Figlet(font='eftiwater')
    print(f.renderText('Audio-Score Meta'))
    f = Figlet(font='sblood')
    print(f.renderText('Dataset'))
    print()

    print("Starting installation")
    print("---------------------")
    print("Author: " + data['author'])
    print("Year: ", data['year'])
    print("Website: ", data['url'])
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
        downloaded_file = ftp_download(item, credential, install_dir,
                                       parsed_url)
    else:
        # http, https
        with alive_bar(
            unknown='notes2', spinner='notes_scrolling'
        ) as bar:
            temp_fn, _header = urlretrieve(item['url'],
                                           filename=os.path.join(
                                               install_dir, 'temp'),
                                           reporthook=lambda x, y, z: bar)
        downloaded_file = [temp_fn]
    return downloaded_file


def chose_install_dir(json_file):
    validator = Validator.from_callable(
        lambda x: os.path.isdir(x) or x == '',
        error_message="Not a directory!",
        move_cursor_to_end=True,
    )
    path_completer = PathCompleter(only_directories=True)

    default_dir = json_file['install_dir'] or './'

    question = "\nPath to install datasets [empty to default " + \
        default_dir + "] "
    install_dir = prompt(question,
                         validator=validator,
                         completer=path_completer)
    if not install_dir:
        if not os.path.isdir(default_dir):
            os.mkdir(default_dir)
        install_dir = default_dir
    json_file['install_dir'] = install_dir
    return install_dir


def main():

    with open('datasets.json') as f:
        json_file = json.load(f)

    intro(json_file)

    f = Figlet(font='digital')
    print(f.renderText("Initial setup"))
    install_dir = chose_install_dir(json_file)
    data = load_definitions()
    print("\n------------------")
    print(f.renderText("Chosing datasets"))
    chose_dataset(data, install_dir)

    # at now, no credential is needed
    print("\n------------------")
    credentials = deque(get_credentials(data))
    print(f.renderText("Processing"))
    for d in data:
        full_path = os.path.join(install_dir, d['name'])
        print("Creating " + d['name'])

        if d['url'] != 'unknown':
            print("Downloading (this can take a looooooooooooooot)...")
            downloaded_file = download(d, credentials, install_dir)

        # unzipping if needed
        if d['unpack']:
            print("Unpacking...")
            for temp_fn in downloaded_file:
                format = ''.join(pathlib.Path(d['url']).suffixes) or '.zip'
                format = [
                    j for i, j in supported_archives.items()
                    if format.endswith(i)
                ][0]
                unpack_archive(temp_fn, full_path, format)
                # cleaning up
                os.remove(temp_fn)

        # post-processing
        if d['post-process'] != 'unknown':
            # the following line is only for POSIX!!!
            print("Post-processing (this could take a biiiiiiiiiiiiiiit)...")
            # recursively concatenate commands
            command = '; '.join(
                list(map(lambda x: ''.join(x), d['post-process'])))
            command = command.replace('&install_dir', json_file['install_dir'])

            # writing commands to temporary file and executing it as a shell
            # script
            with tempfile.NamedTemporaryFile(mode='w+t', delete=False) as tf:
                tf.write(command)
                tf_name = tf.name
                p = Popen(['/bin/env', 'sh', tf_name], stdout=DEVNULL,
                          stderr=DEVNULL)

            # progress bar while script runs
            with alive_bar(
                unknown='notes_scrolling', spinner='notes'
            ) as bar:
                while p.poll() is None:
                    bar()
            os.remove(tf_name)

        print("------------------")

        # just to be sure
        urlcleanup()

    print("\n------------------")
    print(f.renderText("Unpacking ground-truths"))
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
