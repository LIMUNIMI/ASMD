#!/usr/bin/env python3

import codecs
import re
import os
import logging
import sys
import requests
import sqlite3
from string import ascii_lowercase
from bs4 import BeautifulSoup, Tag, NavigableString
from urllib.parse import urljoin

DBNAME = 'kunstderfuge.db'
BASE_URL='http://www.kunstderfuge.com/'

def http_get(url, s):
    """
    Perform an HTTP Get requests.

    Arguments
    ---------
    url : str
        the url
    s : requests.Session
        a Session object

    Returns
    -------
    r : request.Response
        a Response object with an added `success` field (True if response was
        200 and contains html code, False otherwise)

    Note
    ----
    If an exception occurs during requests, this function exits the process
    """

    try:
        r = s.get(url)
    except requests.RequestException as e:
        logging.exception("Error in requesting " + url)
        sys.exit(2)

    content_type = r.headers['Content-Type'].lower()
    if (r.status_code == 200 and content_type is not None and content_type.find('html') > -1):
        r.success = True
    else:
        r.success = False
    return r

def create_db_tables():
    if os.path.exists(DBNAME):
        os.remove(DBNAME)
    db = sqlite3.connect(DBNAME)
    db.execute("""
        CREATE TABLE 'Composers' (
                'ID'	INTEGER PRIMARY KEY AUTOINCREMENT,
                'Surname'	TEXT NOT NULL,
                'Name'	TEXT,
                'Birth'	INTEGER,
                'Death'	INTEGER
        );
    """)
    db.execute("""
        CREATE TABLE 'Songs' (
                'ID'	INTEGER PRIMARY KEY AUTOINCREMENT,
                'Opus'	TEXT,
                'Title'	TEXT NOT NULL,
                'Url'	INTEGER NOT NULL,
                'Composer'	INTEGER,
                FOREIGN KEY('Composer') REFERENCES 'Composers'('ID')
        );
    """)

    db.commit()
    return db

def add_composer(db, composer):
    # extract data from composer
    fields = re.split(", |\(|\)", composer.text)
    surname = ""
    name = ""
    death = "NULL"
    birth = "NULL"
    surname = fields[0]
    if len(fields) > 1:
        name = fields[1]
        if len(fields) > 2:
            dates = []
            for field in fields[2:]:
                # iterating all the remaining splits, extracting dates and concatenating
                # '\D' matches all non-digit characters
                dates += [int(date) for date in re.split('\D', field) if date.isdigit()]
            if len(dates) >= 1:
                birth = dates[0]
            if len(dates) >= 2:
                death = dates[1]
    print("Adding composer", normalize_text(surname), normalize_text(name), birth, '-', death)
    db.execute("""
        INSERT INTO 'Composers'('Surname','Name','Birth','Death')
            VALUES ('{0}', '{1}', {2}, {3});
    """.format(normalize_text(surname), normalize_text(name), birth, death))

def normalize_text(string):
    string = string.replace("'", "")
    return string

def add_song(db, element, url, composer_id):
    opus = ''
    iterator = iter(element.contents)
    if type(element.contents[0]) is NavigableString:
        # call `next` here, otherwise if there is no opus, it skips the first song
        content = next(iterator)
        opus = str(content)
    for content in iterator:
        subopus = ''
        if type(content) is Tag and content.name=='a' and content.text.startswith('»'):
            # this is a new link to a midi file
            midi_url = urljoin(url, content.get('href'))
            content = next(iterator)
            splits = content.split(maxsplit=1)
            if len(splits) > 1:
                title = subopus + splits[1]
            else:
                title = subopus
            print("    Adding song", title, "opus:", opus)
            db.execute("""
                INSERT INTO 'Songs'('Opus', 'Title', 'Url', 'Composer')
                    VALUES ('{0}', '{1}', '{2}', {3})
            """.format(normalize_text(opus), normalize_text(title), normalize_text(midi_url), composer_id))
        if type(content) is NavigableString:
            no_spaces = content.split(maxsplit=1)
            if len(no_spaces) > 1:
                subopus = no_spaces[1] + ' '
        else:
                subopus = ''

def scrape_composer_page(db, session, link, composer_id, url, recursion_level):

    if recursion_level > 1:
        return

    page_url = urljoin(url, link.find_next('a').get('href'))

    print("Scraping page", page_url)

    r = http_get(page_url, session)
    if r.success:
        bs4 = BeautifulSoup(r.text, "html.parser")
        # looking for first midi element
        element = bs4.find('p', {'class': 'midi'})
        if not element:
            # page without midi, onli list of subsections (e.g., bach,
            # beethoven...)
            lists = bs4.find_all('li')
            for list in lists:
                if list.contents[0].name == 'b':
                    # this is a bold element, scraping it
                    link = list.contents[0]
                    scrape_composer_page(db, session, link, composer_id, page_url, recursion_level+1)
            return

        while True:
            # skip all elements with no class
            element = element.find_next_sibling()
            if not element:
                return
            css_class = element.get('class')
            if css_class:
                if css_class[0] == 'midi':
                    add_song(db, element, page_url, composer_id)

def main():
    db = create_db_tables()
    s = requests.Session()
    for character in ascii_lowercase:
        print("Chracter", character)
        url = BASE_URL + 'classical/' + character + '.htm'

        r = http_get(url, s)
        if r.success:
            bs4 = BeautifulSoup(r.text, "html.parser")
            # looking for first midi element
            midi_link = bs4.find('p', {'class': 'midi'})
            # take its parent table
            table = midi_link.find_parent('td')
            # take all the composers
            composers = table.find_all('h1')
            for composer_id, composer in enumerate(composers, start=1):
                add_composer(db, composer)

                # looking for songs from composer
                element = composer
                while True:
                    # skip all elements with no class
                    element = element.find_next_sibling()
                    if not element:
                        break
                    css_class = element.get('class')
                    if css_class:
                        if css_class[0] == 'page':
                            # scrape the linked page
                            if element.text.startswith('›››'):
                                scrape_composer_page(db, s, element, composer_id, url, 0)
                        elif css_class[0] == 'midi':
                            add_song(db, element, url, composer_id)
                    elif element.name == 'h1':
                        break
                db.commit()
        else:
            print("Request not succesful, skipping")

if __name__ == "__main__":
    main()
