#cython: language_level=3
import json
from copy import deepcopy
import tarfile
import os
import gzip
from difflib import SequenceMatcher
from pretty_midi.constants import INSTRUMENT_MAP
from convert_from_file import func_map
import numpy as np
from alignment_stats import seed, fill_stats
import multiprocessing as mp

#: if True, run conversion in parallel processes
PARALLEL = True
# PARALLEL = False


def normalize_text(text):
    return ''.join(ch for ch in text if ch.isalnum()).lower()


def text_similarity(a, b):
    return SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b)).size


# normalizing MIDI instrument names
INSTRUMENT_MAP = list(map(normalize_text, INSTRUMENT_MAP))

INSTRUMENT_MAP.append('drumkit')


def merge_dicts(idx, *args):
    """
    Merges lists of dictionaries, by adding each other the values of
    corresponding dictionaries
    """

    assert all(type(x) is list for x in args), "Input types must be lists"

    assert all(len(x) == len(args[0]) for x in args[1:]
               ), "Cannot merge list with different lenghts"

    idx = min(idx, len(args[0]) - 1)  # For PHENICX

    if len(args) == 1:
        return args[0][idx]

    obj1_copy = deepcopy(args[0][idx])

    for arg in args[1:]:
        arg = arg[idx]
        for key in obj1_copy.keys():
            d1_element = obj1_copy[key]
            if type(d1_element) is dict:
                obj1_copy[key] = merge_dicts(0, [d1_element], [arg[key]])
            elif type(d1_element) is int:
                obj1_copy[key] = min(d1_element, arg[key])
            else:
                obj1_copy[key] = d1_element + arg[key]
        del arg

    return obj1_copy


def misalign(ons_dev, offs_dev, mean, out, stats):
    """
    Given an onset deviation, an offset deviation, a mean, a ground truth
    dictionary and a `alignment_stats.Stats` object, computes onsets and
    offsets misaligned. return 2 lists (onsets, offsets).
    """
    if len(out['precise_alignment']['onsets']) > 0:
        aligned = 'precise_alignment'
    else:
        aligned = 'broad_alignment'
    length = len(out['pitches'])
    seed()
    onsets = stats.get_random_onset_diff(k=length, max=0.1)
    seed()
    offsets = stats.get_random_offset_diff(k=length, max=0.1)
    onsets = np.array(out[aligned]['onsets']) + \
        np.array(onsets) * ons_dev + mean
    offsets = np.array(out[aligned]['offsets']) + \
        np.array(offsets) * offs_dev + mean

    # set first onset to 0
    first_onset = onsets.min()
    onsets -= first_onset
    offsets -= first_onset

    # make each offset being greater than the onset
    def fix_offsets(i):
        if offsets[i] > onsets[i]:
            return offsets[i]
        else:
            return 2*onsets[i] - offsets[i]
    offsets = list(map(fix_offsets, range(len(onsets))))

    return onsets.tolist(), offsets


def conversion(arg):
    """
    A function that is run on each song to convert its ground_truth.
    Intended to be run in parallel.
    """
    l, song, json_file, dataset, stats, ons_dev, offs_dev, mean = arg
    print(" elaborating " + song['title'])
    paths = song['ground_truth']

    to_be_included_in_the_archive = []

    for i, path in enumerate(paths):
        final_path = os.path.join(json_file['install_dir'], path)
        # get the index of the track from the path
        idx = path[path.rfind('-') + 1: path.rfind('.json.gz')]

        # calling each function listed in the map and merge everything

        out = merge_dicts(int(idx), *[func(final_path, **params) for func, params in func_map[dataset['name']]])

        # take the General Midi program number associated with the most
        # similar instrument name
        instrument = normalize_text(song['instruments'][i])
        out['instrument'] = max(
            range(len(INSTRUMENT_MAP)),
            key=lambda x: text_similarity(
                INSTRUMENT_MAP[x], instrument)
        )

        if dataset['ground_truth']['non_aligned'] == 2 and stats:
            # computing deviations for each pitch
            onsets, offsets = misalign(
                ons_dev[l], offs_dev[l], mean[l], out, stats)
            out['non_aligned']['onsets'] = onsets
            out['non_aligned']['offsets'] = offsets

        print("   saving " + final_path)
        json.dump(out, gzip.open(final_path, 'wt'))

        to_be_included_in_the_archive.append(final_path)
    return to_be_included_in_the_archive


def create_gt(data_fn, args, gztar=False):
    """
    Parse the json file `data_fn` and convert all ground_truth to our
    representation. Then dump it according to the specified paths. Finally,
    if `gztar` is True, create a gztar archive called 'ground_truth.tar.gz' in
    this directory containing only the ground truth file in their final
    positions.
    """

    print("Opening JSON file: " + data_fn)

    json_file = json.load(open(data_fn, 'r'))
    if os.path.exists('_alignment_stats.pkl'):
        import pickle
        stats = pickle.load(open('_alignment_stats.pkl', 'rb'))
    else:
        stats = None
    #     stats = fill_stats(['precise_alignment', 'broad_alignment'])
    #     stats.compute_hist()

    to_be_included_in_the_archive = []
    for dataset in json_file['datasets']:
        if len(args) > 1:
            if dataset['name'] not in args:
                continue

        print("\n------------------------\n")
        print("Starting processing " + dataset['name'])
        if dataset['ground_truth']['non_aligned'] == 2 and stats:
            # computing means and std deviations for each song in the dataset
            mean = stats.get_random_mean(k=len(dataset['songs']), max=0.1)
            seed()
            ons_dev = stats.get_random_onset_dev(k=len(dataset['songs']), max=1)
            seed()
            offs_dev = stats.get_random_offset_dev(k=len(dataset['songs']), max=1)
            arg = [(i, song, json_file, dataset, stats, ons_dev, offs_dev, mean)
                   for i, song in enumerate(dataset['songs'])]
        else:
            arg = [(i, song, json_file, dataset, None, None, None, None)
                   for i, song in enumerate(dataset['songs'])]
        if not PARALLEL:
            for l, song in enumerate(dataset['songs']):
                to_be_included_in_the_archive += conversion(arg[l])
        else:
            CPU = os.cpu_count() - 1
            p = mp.Pool(CPU)
            result = p.map_async(
                conversion,
                arg,
                len(dataset['songs']) // CPU + 1
            )
            to_be_included_in_the_archive += sum(result.get(), [])

    # creating the archive
    if gztar:
        print("\n\nCreating the final archive")
        with tarfile.open('ground_truth.tar.gz', mode='w:gz') as tf:
            for fname in to_be_included_in_the_archive:
                tf.add(fname)
