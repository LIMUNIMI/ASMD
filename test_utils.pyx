import json
from fuzzywuzzy import fuzz
import sqlite3 as sql
import numpy as np
from libcpp.string cimport string
from libcpp cimport bool
import multiprocessing as mp
import cython
from cython.parallel import prange

db = sql.connect('./kunstderfuge.db')
count = mp.Value('i', 0)
lock = mp.Lock()

cdef extern from "<cctype>" namespace "std":
    int tolower( int ch )
    int isdigit( int ch )

cdef string split_digits_from_words(string cppstring):
    cdef int i = 0
    while cppstring.length() > i + 1:
        if isdigit(cppstring[i+1]) and not isdigit(cppstring[i]) and cppstring[i] != ' ':
            cppstring.insert(i+1, ' ')
        if not isdigit(cppstring[i+1]) and isdigit(cppstring[i]) and cppstring[i+1] != ' ':
            cppstring.insert(i+1, ' ')
        i+=1
    return cppstring

cdef list get_composer_list(string composer):
    global lock
    with lock:
        query = db.execute("SELECT Opus, Title FROM Composers JOIN Songs ON Composers.ID = Songs.Composer WHERE Composers.Surname = '" + composer.decode('UTF-8') + "'")
    return query.fetchall()

cdef string replace(string cppstring, string a, string b):
    cdef int i
    cdef char c
    for i in range(cppstring.length()):
        c = cppstring[i]
        if c == a[0]:
            cppstring[i] = b[0]
    return cppstring

cdef string norm(string cppstring):
    cdef int i
    for i in range(cppstring.length()):
        cppstring[i] = tolower(cppstring[i])
    cppstring = replace(cppstring, '_', ' ')
    cppstring = replace(cppstring, '-', ' ')
    cppstring = replace(cppstring, '.', ' ')
    cppstring = split_digits_from_words(cppstring)
    return cppstring

cdef list search(string title, string composer):
    title = norm(title)
    cdef list query = get_composer_list(composer)
    if len(query) == 0:
        print('cannot retrieve composer', composer)
    cdef list answer = []
    cdef tuple i
    cdef string fulltitle
    cdef int score
    for i in query:
        fulltitle = norm(i[0].encode('UTF-8') + i[1].encode('UTF-8'))
        score = fuzz.token_set_ratio(title, fulltitle)
        if score > 90:
            answer.append((fulltitle, title, score))
    return answer

def pool_work(song):
    global count
    answer = search(song['title'].encode('UTF-8'), song['composer'].encode('UTF-8'))
    if answer:
        print(len(answer), max(answer, key=lambda x: x[2]))
        count += 1

def full_comparison():
    cdef dict d = json.load(open('datasets.json'))
    cdef dict dataset, song
    cdef list answer
    for dataset in d['datasets']:
        with mp.Pool() as pool:
            pool.map(pool_work, dataset['songs'])

    print(count)
