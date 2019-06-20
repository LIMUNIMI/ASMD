#!/usr/bin/env python3
import yaml
import pretty_midi
from utils import io
from copy import copy
import tarfile

# importing root folder from here
import os
import sys
p = os.path.abspath('../..')
if p not in sys.path:
    sys.path.append(p)


# The dictionary prototype for containing the ground-truth
gt = {
    "precise-alignment": {
        "onsets": [],
        "offsets": []
    },
    "non-aligned": {
        "onsets": [],
        "offsets": []
    },
    "velocities": [],
    "notes": [],
    "pitches": [],
    "f0": [],
}


func_map = {
    'Bach10': [from_bach10_f0, from_mirex_txt],
    'SMD': [from_midi]
}


def from_midi(midi_fn, non_aligned=False):
    """
    Open a midi file `midi_fn` and convert it to our ground-truth
    representation. This fills velocities, pitches and alignment (default:
    `precise-alignment`). Returns a list containing a dictionary
    """
    midi_notes = io.open_midi(midi_fn)
    out = copy(gt)

    if non_aligned:
        alignment = "non-aligned"
    else:
        alignment = "precise-alignment"
    onsets, offsets = out[alignment].values()

    for note_group in midi_notes:
        for note in note_group:
            out["pitches"].append(note.pitch)
            out["velocities"].append(note.velocity)
            onsets.append(note.start)
            offsets.append(note.end)

    return [out]


def from_mirex_txt(txt_fn, sources=[0]):
    """
    Open a txt file `txt_fn` in the MIREX format (Bach10) and convert it to
    our ground-truth representation. This fills: `precise-alignment`, `pitches`.
    `sources` is an iterable containing the indices of the  sources to be
    considered, where the first source is 0. Returns a list of dictionary, one
    per source.
    """
    out_list = list()

    with open(txt_fn) as f:
        lines = f.readlines()

    for source in sources:
        out = copy(gt)
        for line in lines:
            fields = line.split(' ')
            if int(fields[-1] - 1) == source:
                out["pitches"].append(fields[2])
                out["precise_alignment"]["onsets"].append(fields[0]) / 1000.
                out["precise_alignment"]["offsets"].append(fields[1]) / 1000.
        out_list.append(out)

    return out_list


def from_bach10_f0(nmat_fn, sources=[0]):
    """
    Open a matlab mat file `nmat_fn` in the MIREX format (Bach10) for frame
    evaluation and convert it to our ground-truth representation. This fills:
    `f0`.  `sources` is an iterable containing the indices of the  sources to
    be considered, where the first source is 0.  Returns a list of dictionary,
    one per source.
    """
    out_list = list()

    import scipy.io
    f0s = scipy.io.loadmat(nmat_fn)['GTF0s']
    for source in sources:
        out = copy('gt')
        out["f0"] = f0s[source]
        out_list.append(out)

    return out_list


def merge(obj1, obj2):
    """
    Merge two lists of dictionaries, by adding each other the values of
    corresponding dictionaries
    """

    assert len(obj1) == len(obj2), "Cannot merge list with different lenghts"

    assert type(obj1) == type(obj2) == list, "Input types must be lists"

    obj1_copy = copy(obj1)
    for i, d1 in enumerate(obj1_copy):
        d2 = obj2[i]
        for key in d1.keys():
            d1[key].append(d2[key])

    return obj1_copy


def from_csv(csv_fn):
    """
    Open a csv file `csv_fn` and convert it to our ground-truth representation.
    """
    return copy(gt)


def create_gt(data_fn, xztar=False):
    """
    Parse the yaml file `data_fn` and convert all ground-truth to our
    representation. Then dump it according to the specified paths. Finally,
    if `xztar` is True, create a xztar archive called 'ground-truth.tar.xz' in
    this directory containing only the ground truth file in their final
    positions.
    """

    with open(data_fn) as f:
        yaml_file = yaml.safe_load(f)

    to_be_included_in_the_archive = []
    for dataset in yaml_file['datasets']:
        for song in dataset['songs']:
            input_path = 'something'  # THE PROBLEM IS HERE
            final_path = song['ground-truth']

            # calling each function listed in the map and merge everything
            out = merge(*[func(input_path)
                          for func in func_map[dataset['name']]])

            with open(final_path, 'w') as f:
                yaml.safe_dump(out, f)

            to_be_included_in_the_archive.append(final_path)

    # creating the archive
    with tarfile.open('ground-truth.tar.xz', mode='w:xz') as tf:
        for fname in to_be_included_in_the_archive:
            tf.add(fname)


if __name__ == "__main__":
    create_gt('datasets.yaml', xztar=True)
