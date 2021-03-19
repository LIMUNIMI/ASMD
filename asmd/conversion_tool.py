import gzip
import json
import multiprocessing as mp
import os
import tarfile
from copy import deepcopy
from difflib import SequenceMatcher
from os.path import join as joinpath

import numpy as np
from pretty_midi.constants import INSTRUMENT_MAP

from .alignment_stats import Stats
from .asmd import load_definitions
from .convert_from_file import *
from .idiot import THISDIR

# this is only for detecting the package path

#: if True, run conversion in parallel processes
PARALLEL = True
# PARALLEL = False


def normalize_text(text):
    return ''.join(ch for ch in text if ch.isalnum()).lower()


def text_similarity(a, b):
    return SequenceMatcher(None, a,
                           b).find_longest_match(0, len(a), 0, len(b)).size


# normalizing MIDI instrument names
INSTRUMENT_MAP = list(map(normalize_text, INSTRUMENT_MAP))

INSTRUMENT_MAP.append('drumkit')


def merge_dicts(idx, *args):
    """
    Merges lists of dictionaries, by adding each other the values of
    corresponding dictionaries

    `args` can contain `None` values (except for the first one); in such case,
    that argument will be skipped; this is useful if a dataset contains
    annotations not for all the files (e.g. ASAP annotations for Maestro
    dataset)
    """

    assert all(type(x) is list or x is None
               for x in args), "Input types must be lists or None"

    assert all(len(x) == len(args[0]) for x in args[1:]
               if x is not None), "Cannot merge list with different lenghts"

    idx = min(idx, len(args[0]) - 1)  # For PHENICX

    if len(args) == 1:
        return args[0][idx]

    obj1_copy = deepcopy(args[0][idx])

    for arg in args[1:]:
        if arg is not None:
            arg = arg[idx]
            for key in obj1_copy.keys():
                d1_element = obj1_copy[key]
                if type(d1_element) is dict:
                    obj1_copy[key] = merge_dicts(0, [d1_element], [arg[key]])
                elif type(d1_element) is int:
                    obj1_copy[key] = min(d1_element, arg[key])
                else:
                    obj1_copy[key] = d1_element + arg[key]
        # del arg

    return obj1_copy


def misalign(out, stats):
    """
    Given a ground truth dictionary and a `alignment_stats.Stats` object,
    computes onsets and offsets misaligned. Return 3 lists (pitches, onsets,
    offsets).
    """
    if len(out['precise_alignment']['onsets']) > 0:
        aligned = 'precise_alignment'
    else:
        aligned = 'broad_alignment'
    onsets = stats.get_random_onsets(np.array(out[aligned['onsets']]))
    offsets = stats.get_random_offets(np.array(out[aligned['offsets']]))
    pitches = out[aligned]['pitches']

    # set first onset to 0
    first_onset = onsets.min()
    onsets -= first_onset
    offsets -= first_onset

    # a table to search for same pitches
    table_pitches = [[]] * 128
    for i, p in enumerate(pitches):
        table_pitches[int(p)].append(i)

    # make each offset being greater than the onset
    # but smaller than the following onset in the
    # same pitch
    def fix_offsets(i):

        ret = offsets[i]
        if offsets[i] <= onsets[i]:
            ret = 2 * onsets[i] - offsets[i]

        # search next note with same pitch
        j = None
        for k in table_pitches[int(pitches[i])]:
            if onsets[k] > onsets[i]:
                j = k
                break

        if j is not None and j < len(onsets):
            if ret > onsets[j]:
                ret = onsets[j] - 0.005

        return ret

    offsets = list(map(fix_offsets, range(len(onsets))))

    return pitches, onsets.tolist(), offsets


def conversion(arg):
    """
    A function that is run on each song to convert its ground_truth.
    Intended to be run in parallel.
    """
    l, song, json_file, dataset, stats = arg
    print(" elaborating " + song['title'])
    paths = song['ground_truth']

    to_be_included_in_the_archive = []

    for i, path in enumerate(paths):
        final_path = os.path.join(json_file['install_dir'], path)
        # get the index of the track from the path
        idx = path[path.rfind('-') + 1:path.rfind('.json.gz')]

        # calling each function listed in the map and merge everything

        out = merge_dicts(
            int(idx), *[
                eval(func)(final_path, **params)
                for func, params in dataset["install"]["conversion"]
            ])

        # take the General Midi program number associated with the most
        # similar instrument name
        instrument = normalize_text(song['instruments'][i])
        out['instrument'] = max(
            range(len(INSTRUMENT_MAP)),
            key=lambda x: text_similarity(INSTRUMENT_MAP[x], instrument))

        # check if at least one group to which this song belongs to has
        # `misaligned` set to 2
        misaligned = False
        for group in song['groups']:
            dataset['ground_truth'][group]['misaligned'] == 2
            misaligned = True
            break

        if misaligned and stats:
            # computing deviations for each pitch
            stats.new_song(seed=l)
            pitches, onsets, offsets = misalign(out, stats)
            out['misaligned']['onsets'] = onsets
            out['misaligned']['offsets'] = offsets
            out['misaligned']['pitches'] = pitches
            # computing the percentage of missing and extra notes (between 0.05
            # and 0.15)
            m = np.random.rand() % 0.1 + 0.05
            e = np.random.rand() % 0.1 + 0.05
            mask = np.random.choice([0, 1, 2], p=[m, e, 1-e-m], size=pitches.shape)
            out['missing'] = mask == 0
            out['extra'] = mask == 1

        print("   saving " + final_path)
        # pretty printing stolen from official docs
        json.dump(out, gzip.open(final_path, 'wt'), sort_keys=True, indent=4)

        to_be_included_in_the_archive.append(final_path)
    return to_be_included_in_the_archive


def create_gt(data_fn,
              gztar=False,
              alignment_stats: Stats = None,
              whitelist=[],
              blacklist=[]):
    """
    Parse the json file `data_fn` and convert all ground_truth to our
    representation. Then dump it according to the specified paths. Finally,
    if `gztar` is True, create a gztar archive called 'ground_truth.tar.gz' in
    this directory containing only the ground truth file in their final
    positions.

    If ``alignment_stats`` is not None, it should be an object of type
    ``alignment_stats.Stats`` as the one returned by ``alignment_stats.main``
    """

    print("Opening JSON file: " + data_fn)

    json_file = json.load(open(data_fn, 'r'))

    to_be_included_in_the_archive = []
    datasets = load_definitions(joinpath(THISDIR, 'definitions'))
    for dataset in datasets:
        if blacklist:
            if dataset['name'] in blacklist:
                print(dataset['name'] + " in blacklist!")
                continue

        if whitelist:
            if dataset['name'] not in whitelist:
                print(dataset['name'] + " not in whitelist!")
                continue

        if not os.path.exists(
                os.path.join(json_file["install_dir"], dataset["name"])):
            print(dataset["name"] + " not installed, skipping it")
            continue

        print("\n------------------------\n")
        print("Starting processing " + dataset['name'])
        arg = [
            (i, song, json_file, dataset, alignment_stats)
            for i, song in enumerate(dataset['songs'])
        ]
        if not PARALLEL:
            for i in range(len(dataset['songs'])):
                to_be_included_in_the_archive += conversion(arg[i])
        else:
            CPU = os.cpu_count() - 1  # type: ignore
            p = mp.Pool(CPU)
            result = p.map_async(conversion, arg,
                                 len(dataset['songs']) // CPU + 1)
            to_be_included_in_the_archive += sum(result.get(), [])

    def _remove_basedir(x):
        x.name = x.name.replace(json_file['install_dir'][1:] + '/', '')
        return x

    # creating the archive
    if gztar:
        print("\n\nCreating the final archive")
        with tarfile.open('ground_truth.tar.gz', mode='w:gz') as tf:
            for fname in to_be_included_in_the_archive:
                # adding file with relative path
                tf.add(fname, filter=_remove_basedir)
