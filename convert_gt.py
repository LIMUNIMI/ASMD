#!/usr/bin/env python3
import json
import pretty_midi
import scipy.io
from utils import io
from copy import deepcopy
import tarfile
import sys
import os
import csv
import gzip
from difflib import SequenceMatcher
from pretty_midi.constants import INSTRUMENT_MAP


def normalize_text(text):
    return ''.join(ch for ch in text if ch.isalnum()).lower()

def text_similarity(a, b):
    return SequenceMatcher(None, a, b).find_longest_match(0, len(a), 0, len(b)).size

# normalizing MIDI instrument names
INSTRUMENT_MAP = list(map(normalize_text, INSTRUMENT_MAP))

INSTRUMENT_MAP.append('drumkit')

# The dictionary prototype for containing the ground_truth
gt = {
    "precise_alignment": {
        "onsets": [],
        "offsets": []
    },
    "non_aligned": {
        "onsets": [],
        "offsets": []
    },
    "broad_alignment": {
        "onsets": [],
        "offsets": []
    },
    "velocities": [],
    "notes": [],
    "pitches": [],
    "f0": [],
    "instrument": 255
}


def change_ext(input_fn, new_ext, no_dot=False):
    """
    Return the input path `input_fn` with `new_ext` as extension.
    If `no_dot` is True, it will not add a dot before of the extension,
    otherwise it will add it if not present.
    """

    root = input_fn[ :input_fn.rfind('-')]
    if not new_ext.startswith('.'):
        if not no_dot:
            new_ext = '.' + new_ext

    return root + new_ext


def from_midi(midi_fn, alignment='precise_alignment', pitches=True, velocities=True, merge=True):
    """
    Open a midi file `midi_fn` and convert it to our ground_truth
    representation. This fills velocities, pitches and alignment (default:
    `precise_alignment`). Returns a list containing a dictionary. `alignment`
    can also be `None` or `False`, in that case no alignment is filled. If `merge` is
    True, the returned list will contain a dictionary for each track.
    """
    new_midi_fn = change_ext(midi_fn, '.mid')
    if not os.path.exists(new_midi_fn):
        new_midi_fn = change_ext(midi_fn, '.midi')

    midi_tracks = io.open_midi(new_midi_fn, merge=merge)

    out = list()

    if merge:
        midi_tracks = [midi_tracks]

    for track in midi_tracks:
        data = deepcopy(gt)

        if alignment:
            onsets, offsets = data[alignment].values()

        for note_group in track:
            for note in note_group:
                if pitches:
                    data["pitches"].append(note.pitch)
                if velocities:
                    data["velocities"].append(note.velocity)
                if alignment:
                    onsets.append(float(note.start))
                    offsets.append(float(note.end))
        out.append(data)


    return out


def from_phenicx_txt(txt_fn, non_aligned=False):
    """
    Open a txt file `txt_fn` in the PHENICX format and convert it to our
    ground_truth representation. This fills: `broad_alignment`.
    """
    out_list = list()
    txt_fn = change_ext(txt_fn, 'txt')

    with open(txt_fn) as f:
        lines = f.readlines()

    out = deepcopy(gt)
    for line in lines:
        fields = line.split(',')
        out["notes"].append(fields[2])
        out["broad_alignment"]["onsets"].append(float(fields[0]))
        out["broad_alignment"]["offsets"].append(float(fields[1]))
    out_list.append(out)

    return out_list


def from_bach10_txt(txt_fn, sources=range(4)):
    """
    Open a txt file `txt_fn` in the MIREX format (Bach10) and convert it to
    our ground_truth representation. This fills: `precise_alignment`, `pitches`.
    `sources` is an iterable containing the indices of the  sources to be
    considered, where the first source is 0. Returns a list of dictionary, one
    per source.
    """
    out_list = list()
    txt_fn = change_ext(txt_fn, 'txt')

    with open(txt_fn) as f:
        lines = f.readlines()

    for source in sources:
        out = deepcopy(gt)
        for line in lines:
            fields = line.split('\t')
            if int(fields[-1]) - 1 == source:
                out["pitches"].append(int(fields[2]))
                out["precise_alignment"]["onsets"].append(float(fields[0]) / 1000.)
                out["precise_alignment"]["offsets"].append(float(fields[1]) / 1000.)
        out_list.append(out)


    return out_list


def from_bach10_f0(nmat_fn, sources=range(4)):
    """
    Open a matlab mat file `nmat_fn` in the MIREX format (Bach10) for frame
    evaluation and convert it to our ground_truth representation. This fills:
    `f0`.  `sources` is an iterable containing the indices of the  sources to
    be considered, where the first source is 0.  Returns a list of dictionary,
    one per source.
    """
    out_list = list()
    nmat_fn = change_ext(nmat_fn, '-GTF0s.mat', no_dot=True)

    f0s = scipy.io.loadmat(nmat_fn)['GTF0s']
    for source in sources:
        out = deepcopy(gt)
        out["f0"] = f0s[source].tolist()
        out_list.append(out)


    return out_list


def from_musicnet_csv(csv_fn, fr=44100.0):
    """
    Open a csv file `csv_fn` and convert it to our ground_truth representation.
    This fills: `broad_alignment`, `non_aligned`, `pitches`.
    This returns a list containing only one dict. `fr` is the framerate of the
    audio files (MusicNet csv contains the frame number as onset and offsets of
    each note) and it shold be a float.

    N.B. MusicNet contains wav files at 44100 Hz as framerate.
    """
    csv_fn = change_ext(csv_fn, 'csv')
    data = csv.reader(open(csv_fn), delimiter=',')
    out = deepcopy(gt)

    # skipping first line
    next(data)

    for row in data:
        # converting everything to float, except the last onw that is the
        # duration name as string
        row = list(map(float, row[:-1]))

        out["broad_alignment"]["onsets"].append((row[0]) / fr)
        out["broad_alignment"]["offsets"].append(row[1] / fr)
        out["pitches"].append(int(row[3]))
        out["non_aligned"]["onsets"].append(row[4])
        out["non_aligned"]["offsets"].append(row[4] + row[5])

    return [out]


def merge_dicts(idx, *args):
    """
    Merges lists of dictionaries, by adding each other the values of
    corresponding dictionaries
    """

    assert all(type(x) is list for x in args), "Input types must be lists"

    assert all(len(x) == len(args[0]) for x in args[1:]), "Cannot merge list with different lenghts"

    idx = min(idx, len(args[0]) - 1) # For PHENICX

    if len(args) == 1:
        return args[0][idx]

    obj1_copy = deepcopy(args[0][idx])
    for arg in args:
        arg = arg[idx]
        for key in obj1_copy.keys():
            d1_element = obj1_copy[key]
            if type(d1_element) is dict:
                obj1_copy[key] = merge_dicts(0, [d1_element], [arg[key]])
            else:
                obj1_copy[key] = d1_element + arg[key]
        del arg
                # d1_element.append(d2[key])

    return obj1_copy


func_map = {
    'Bach10': [(from_bach10_f0, {}), (from_bach10_txt, {}), (from_midi, {'alignment': 'non_aligned', 'pitches': False, 'velocities': False, 'merge': False})],
    'SMD': [(from_midi, {})],
    'PHENICX': [(from_phenicx_txt, {})],
    'MusicNet': [(from_musicnet_csv, {})],
    'TRIOS_dataset': [(from_midi, {})],
    'Maestro': [(from_midi, {})]
}


def create_gt(data_fn, args, gztar=False):
    """
    Parse the yaml file `data_fn` and convert all ground_truth to our
    representation. Then dump it according to the specified paths. Finally,
    if `gztar` is True, create a gztar archive called 'ground_truth.tar.gz' in
    this directory containing only the ground truth file in their final
    positions.
    """

    print("Opening JSON file: " + data_fn)

    json_file = json.load(open(data_fn, 'r'))

    to_be_included_in_the_archive = []
    for dataset in json_file['datasets']:
        if dataset['name'] in args:
            continue

        print("\n------------------------\n")
        print("Starting processing " + dataset['name'])
        for song in dataset['songs']:
            print(" elaborating " + song['title'])
            paths = song['ground_truth']

            for i, path in enumerate(paths):
                final_path = os.path.join(json_file['install_dir'], path)
                # get the index of the track from the path
                idx = path[path.rfind('-') + 1 : path.rfind('.json.gz')]

                # calling each function listed in the map and merge everything
                out = merge_dicts(int(idx), *[func(final_path, **params)
                              for func, params in func_map[dataset['name']]])

                # take the General Midi program number associated with the most
                # similar instrument name
                instrument = normalize_text(song['instruments'][i])
                out['instrument'] = max(
                    range(len(INSTRUMENT_MAP)),
                    key=lambda x: text_similarity(INSTRUMENT_MAP[x], instrument)
                )

                print("   saving " + final_path)
                json.dump(out, gzip.open(final_path, 'wt'))

            to_be_included_in_the_archive.append(final_path)

    # creating the archive
    if gztar:
        print("\n\nCreating the final archive")
        with tarfile.open('ground_truth.tar.gz', mode='w:gz') as tf:
            for fname in to_be_included_in_the_archive:
                tf.add(fname)


if __name__ == "__main__":
    print("Usage: ")
    print("  python3 convert_gt.py [list of datasets to be excluded]")
    print()

    create_gt('datasets.json', sys.argv, gztar=True)
