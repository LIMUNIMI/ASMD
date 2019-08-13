# cython: language_level=3
import json
from fuzzywuzzy import fuzz
import sqlite3 as sql
import numpy as np
import psutil
from libcpp.string cimport string
from libcpp.vector cimport vector
from libcpp cimport bool
import multiprocessing as mp
import cython
from cython.parallel import prange

lock = mp.Lock()

cdef extern from "<cctype>" namespace "std":
    int tolower( int ch ) nogil
    int isdigit( int ch ) nogil

cdef string split_digits_from_words(string cppstring) nogil:
    cdef size_t i = 0
    while cppstring.length() > i + 1:
        if isdigit(cppstring[i+1]) and not isdigit(cppstring[i]) and cppstring[i] != b' ':
            cppstring.insert(i+1, b' ')
        if not isdigit(cppstring[i+1]) and isdigit(cppstring[i]) and cppstring[i+1] != b' ':
            cppstring.insert(i+1, b' ')
        i+=1
    return cppstring

cdef vector[vector[string]] get_composer_list(string composer):
    db = sql.connect('./kunstderfuge.db')
    db.text_factory = bytes
    query = db.execute("SELECT Opus, Title FROM Composers JOIN Songs ON Composers.ID = Songs.Composer WHERE Composers.Surname = '" + composer.decode('UTF-8') + "'")
    return <vector[vector[string]]> query.fetchall()

cdef string replace(string cppstring, string a, string b) nogil:
    cdef size_t i
    cdef char c
    for i in range(cppstring.length()):
        c = cppstring[i]
        if c == a[0]:
            cppstring[i] = b[0]
    return cppstring

cdef string norm(string cppstring):
    cdef size_t i
    for i in range(cppstring.length()):
        cppstring[i] = tolower(cppstring[i])
    cppstring = replace(cppstring, b'_', b' ')
    cppstring = replace(cppstring, b'-', b' ')
    cppstring = replace(cppstring, b'.', b' ')
    cppstring = split_digits_from_words(cppstring)
    return cppstring

cdef vector[vector[string]] search(string title, string composer):
    cdef vector[vector[string]] query
    cdef size_t score
    cdef string fulltitle
    cdef vector[string] i
    title = norm(title)
    query = get_composer_list(composer)
    if query.size() == 0:
        print('cannot retrieve composer', composer)
    cdef vector[vector[string]] answer
    for i in query:
        fulltitle = norm(i[0] + i[1])
        score = fuzz.token_set_ratio(title, fulltitle)
        if score > 90:
            answer.push_back(<vector[string]> [fulltitle, title, str(score).encode('UTF-8')])
    return answer

def pool_work(song):
    cdef string composer, title
    title = song['title'].encode('UTF-8')
    composer = song['composer'].encode('UTF-8')
    cdef vector[vector[string]] answer
    answer = search(title, composer)
    if answer.size() > 0:
        print(answer.size(), max(answer, key=lambda x: int(x[2])))
        return 1
    else:
        return 0

def full_comparison():
    cdef dict d = json.load(open('datasets.json'))
    cdef dict dataset
    cdef size_t chunksize, cpu_count = psutil.cpu_count() - 1
    cdef int count = 0
    for dataset in d['datasets']:
        chunksize = int(len(d['datasets']) / cpu_count) + 1
        with mp.Pool(cpu_count) as pool:
            counts = pool.imap_unordered(pool_work, dataset['songs'], chunksize=chunksize)
            count += sum(counts)
    print(count)
