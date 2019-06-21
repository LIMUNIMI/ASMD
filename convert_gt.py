#!/usr/bin/env python3
import yaml
import pretty_midi
from utils import io
from copy import copy
import tarfile
import os


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
    'Bach10': [(from_bach10_f0, {}), (from_bach10_txt, {}), (from_midi, {'alignment': 'non_aligned', 'pitches': False, 'velocities': False, 'merge': False})],
    'SMD': [(from_midi, {})],
    'PHENICX': [(from_phenicx_txt, {}), (from_midi, {'alignment': 'non_aligned'})],
    'MusicNet': [(from_csv), {}],
    'TRIOS_dataset': [(from_midi, {})],
    'Maestro': [(from_midi, {})]
}


def change_ext(input_fn, new_ext):
    """
    Return the input path `input_fn` with `new_ext` as extension
    """

    root, _ = os.path.splitext(input_fn)
    if not new_ext.startswith('.'):
        new_ext = '.' + 'new_ext'
        return root + new_ext


def from_midi(midi_fn, alignment='precise_alignment', pitches=True, velocities=True, merge=False):
    """
    Open a midi file `midi_fn` and convert it to our ground-truth
    representation. This fills velocities, pitches and alignment (default:
    `precise-alignment`). Returns a list containing a dictionary. `non_aligned`
    can also be `None`, in that case no alignment is filled. If `merge` is
    True, the returned list will contain a dictionary for each track.
    """
    midi_fn = change_ext(midi_fn, '.mid')
    if not os.path.exists(midi_fn):
        midi_fn = change_ext(midi_fn, '.midi')

    midi_tracks = io.open_midi(midi_fn, merge=merge)

    out = list()

    if merge:
        midi_tracks = [midi_tracks]

    for track in midi_tracks:
        data = copy(gt)

        if alignment in data:
            onsets, offsets = data[alignment].values()
            alignment = True
        else:
            alignment = False

        for note_group in track:
            for note in note_group:
                if pitches:
                    data["pitches"].append(note.pitch)
                if velocities:
                    data["velocities"].append(note.velocity)
                if alignment:
                    onsets.append(note.start)
                    offsets.append(note.end)
        out.append(data)

    return out


def from_phenicx_txt(txt_fn, non_aligned=False):
    """
    Open a txt file `txt_fn` in the PHENICX format and convert it to our
    ground-truth representation. This fills: `precise_alignment`.
    """
    out_list = list()
    txt_fn = change_ext(txt_fn, 'txt')

    with open(txt_fn) as f:
        lines = f.readlines()

    out = copy(gt)
    for line in lines:
        fields = line.split(',')
        out["notes"].append(fields[2])
        out["precise_alignment"]["onsets"].append(float(fields[0]))
        out["precise_alignment"]["offsets"].append(float(fields[1]))
    out_list.append(out)

    return out_list


def from_bach10_txt(txt_fn, sources=range(4)):
    """
    Open a txt file `txt_fn` in the MIREX format (Bach10) and convert it to
    our ground-truth representation. This fills: `precise-alignment`, `pitches`.
    `sources` is an iterable containing the indices of the  sources to be
    considered, where the first source is 0. Returns a list of dictionary, one
    per source.
    """
    out_list = list()
    txt_fn = change_ext(txt_fn, 'txt')

    with open(txt_fn) as f:
        lines = f.readlines()

    for source in sources:
        out = copy(gt)
        for line in lines:
            fields = line.split(' ')
            if int(fields[-1] - 1) == source:
                out["pitches"].append(int(fields[2]))
                out["precise_alignment"]["onsets"].append(float(fields[0]) / 1000.)
                out["precise_alignment"]["offsets"].append(float(fields[1]) / 1000.)
        out_list.append(out)

    return out_list


def from_bach10_f0(nmat_fn, sources=range(4)):
    """
    Open a matlab mat file `nmat_fn` in the MIREX format (Bach10) for frame
    evaluation and convert it to our ground-truth representation. This fills:
    `f0`.  `sources` is an iterable containing the indices of the  sources to
    be considered, where the first source is 0.  Returns a list of dictionary,
    one per source.
    """
    out_list = list()
    nmat_fn = change_ext(nmat_fn, '.mat')

    import scipy.io
    f0s = scipy.io.loadmat(nmat_fn)['GTF0s']
    for source in sources:
        out = copy('gt')
        out["f0"] = f0s[source]
        out_list.append(out)

    return out_list


def from_csv(csv_fn):
    """
    Open a csv file `csv_fn` and convert it to our ground-truth representation.
    """
    csv_fn = change_ext(csv_fn, 'csv')

    return copy(gt)


def merge(*args):
    """
    Merges lists of dictionaries, by adding each other the values of
    corresponding dictionaries
    """

    assert all(type(x) is list for x in args), "Input types must be lists"

    assert all(len(x) == len(args[0]) for x in args[1:]), "Cannot merge list with different lenghts"

    obj1_copy = copy(args[0])
    for i, d1 in enumerate(obj1_copy):
        for arg in args:
            d2 = arg[i]
            for key in d1.keys():
                d1[key].append(d2[key])

    return obj1_copy


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
            out = merge(*[func(input_path, **params)
                          for func, params in func_map[dataset['name']]])

            with open(final_path, 'w') as f:
                yaml.safe_dump(out, f)

            to_be_included_in_the_archive.append(final_path)

    # creating the archive
    with tarfile.open('ground-truth.tar.xz', mode='w:xz') as tf:
        for fname in to_be_included_in_the_archive:
            tf.add(fname)


if __name__ == "__main__":
    create_gt('datasets.yaml', xztar=True)
