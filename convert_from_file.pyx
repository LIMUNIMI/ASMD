#cython: language_level=3
from copy import deepcopy
import os
import csv
import numpy as np
import scipy.io
from utils import io, utils
import re
import pretty_midi

BPM = 20


# The dictionary prototype for containing the ground_truth
gt = {
    "precise_alignment": {
        "onsets": [],
        "offsets": [],
        "pitches": [],
        "notes": [],
        "velocities": []
    },
    "non_aligned": {
        "onsets": [],
        "offsets": [],
        "pitches": [],
        "notes": [],
        "velocities": []
    },
    "broad_alignment": {
        "onsets": [],
        "offsets": [],
        "pitches": [],
        "notes": [],
        "velocities": []
    },
    "f0": [],
    "instrument": 255,
    "beats_non_aligned": []
}


def change_ext(input_fn, new_ext, no_dot=False, remove_player=False):
    """
    Return the input path `input_fn` with `new_ext` as extension.
    If `no_dot` is True, it will not add a dot before of the extension,
    otherwise it will add it if not present.
    `remove_player` can be used to remove the name of the player in the last
    part of the file name when: use this for the `traditional_flute` dataset.
    """

    root = input_fn[:input_fn.rfind('-')]
    if remove_player:
        root = root[:root.rfind('_')]
    if not new_ext.startswith('.'):
        if not no_dot:
            new_ext = '.' + new_ext

    return root + new_ext


def from_midi(midi_fn, alignment='precise_alignment', pitches=True, velocities=True, merge=True, beats=False, remove_player=False):
    """
    Open a midi file `midi_fn` and convert it to our ground_truth
    representation. This fills velocities, pitches, beats and alignment (default:
    `precise_alignment`). Returns a list containing a dictionary. `alignment`
    can also be `None` or `False`, in that case no alignment is filled. If `merge` is
    True, the returned list will contain a dictionary for each track.
    `remove_player` can be used to remove the name of the player in the last
    part of the file name: use this for the `traditional_flute` dataset.
    Beats are filled according to tempo changes.
    """
    new_midi_fn = change_ext(midi_fn, '.mid', remove_player=remove_player)
    if not os.path.exists(new_midi_fn):
        new_midi_fn = change_ext(midi_fn, '.midi', remove_player=remove_player)

    midi_tracks, pm = io.open_midi(new_midi_fn, merge=merge, pm_object=True)

    out = list()

    if merge:
        midi_tracks = [midi_tracks]

    this_bpm = pm.get_tempo_changes()[1][0]
    if alignment == 'non_aligned':
        bpm_ratio = this_bpm / BPM
    else:
        bpm_ratio = 1

    for track in midi_tracks:
        data = deepcopy(gt)

        for note_group in track:
            for note in note_group:
                if pitches:
                    data[alignment]["pitches"].append(note.pitch)
                if velocities:
                    data[alignment]["velocities"].append(note.velocity)
                if alignment:
                    data[alignment]["onsets"].append(float(note.start) * bpm_ratio)
                    data[alignment]["offsets"].append(float(note.end) * bpm_ratio)
        if beats:
            data["beats_non_aligned"] = (pm.get_beats() * bpm_ratio).tolist()
        out.append(data)

    return out


def from_phenicx_txt(txt_fn, non_aligned=False):
    """
    Open a txt file `txt_fn` in the PHENICX format and convert it to our
    ground_truth representation. This fills: `broad_alignment` and 
    `pitches` and `notes` of `non_aligned`.
    """
    out_list = list()
    txt_fn = change_ext(txt_fn, 'txt')

    with open(txt_fn) as f:
        lines = f.readlines()

    out = deepcopy(gt)
    for line in lines:
        fields = re.split(',|\n', line)
        out["non_aligned"]["notes"].append(fields[2])
        out["non_aligned"]["pitches"].append(pretty_midi.note_name_to_number(fields[2]))
        out["broad_alignment"]["notes"].append(fields[2])
        out["broad_alignment"]["pitches"].append(pretty_midi.note_name_to_number(fields[2]))
        out["broad_alignment"]["onsets"].append(float(fields[0]))
        out["broad_alignment"]["offsets"].append(float(fields[1]))
        out_list.append(out)

    return out_list


def from_bach10_mat(mat_fn, sources=range(4)):
    """
    Open a txt file `txt_fn` in the MIREX format (Bach10) and convert it to
    our ground_truth representation. This fills: `precise_alignment`, `pitches`.
    `sources` is an iterable containing the indices of the  sources to be
    considered, where the first source is 0. Returns a list of dictionary, one
    per source.
    """
    out_list = list()
    mat_fn = change_ext(mat_fn, '-GTNotes.mat', no_dot=True)

    mat = scipy.io.loadmat(mat_fn)['GTNotes']
    for i in range(len(mat)):
        out = deepcopy(gt)
        source = mat[i, 0]
        for j in range(len(source)):
            note = source[j, 0]
            out["precise_alignment"]["pitches"].append(np.median(np.rint(note[1, :])))
            out["precise_alignment"]["onsets"].append(
                (note[0, 0] - 2) * 10 / 1000.)
            out["precise_alignment"]["offsets"].append(
                (note[0, -1] - 2) * 10 / 1000.)
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

        out["broad_alignment"]["onsets"].append(int(row[0]) / fr)
        out["broad_alignment"]["offsets"].append(int(row[1]) / fr)
        out["instrument"] = int(row[2])
        out["broad_alignment"]["pitches"].append(int(row[3]))
        out["non_aligned"]["pitches"].append(int(row[3]))
        out["non_aligned"]["onsets"].append(float(row[4]) * 60 / BPM)
        out["non_aligned"]["offsets"].append(float(row[4] * 60 / BPM) + float(row[5]) * 60 / BPM)

    out["beats_non_aligned"] = [i for i in range(int(max(out["non_aligned"]["offsets"])) + 1)]
    return [out]


def from_sonic_visualizer(gt_fn, alignment='precise_alignment'):
    """
    Takes a filename of a sonic visualizer output file  exported as 'csv' and fills the
    'alignment' specified
    """
    gt_fn = change_ext(gt_fn, '.gt')

    data = csv.reader(open(gt_fn), delimiter=',')
    out = deepcopy(gt)
    for row in data:
        out[alignment]["onsets"].append(float(row[0]))
        out[alignment]["offsets"].append(float(row[0]) + float(row[2]))
        p = float(row[1])
        if p == 0:
            p += 1
        pitch = utils.f0_to_midi_pitch(p)
        out[alignment]["pitches"].append(pitch)

    return [out]


#: a dictionary which maps each dataset to a set of functions
func_map = {
    'Bach10': [
        (from_bach10_f0, {}),
        (from_bach10_mat, {}),
        (from_midi,
         {
             'alignment': 'non_aligned',
             'pitches': True,
             'velocities': False,
             'merge': False,
             'beats': True
         }
         )
    ],
    'SMD': [
        (from_midi, {})
    ],
    'PHENICX': [
        (from_phenicx_txt, {})
    ],
    'MusicNet': [
        (from_musicnet_csv, {})
    ],
    'TRIOS_dataset': [
        (from_midi, {})
    ],
    'Maestro': [
        (from_midi, {})
    ],
    'traditional_flute': [
        (from_midi, {
            'alignment': 'non_aligned',
            'pitches': True,
            'velocities': False,
            'merge': False,
            'remove_player': True,
            'beats': True
        }),
        (from_sonic_visualizer, {})
    ],
    'vienna_corpus': [
        (from_midi, {
            'alignment': 'non_aligned',
            'pitches': True,
            'velocities': False,
            'merge': True,
            'remove_player': True,
            'beats': True
        }),
        (from_midi, {
            'alignment': 'precise_alignment',
            'pitches': True,
            'velocities': True,
            'merge': True,
            'remove_player': False
        })
    ]
}
