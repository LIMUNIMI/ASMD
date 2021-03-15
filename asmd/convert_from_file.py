import csv
import os
import re
from copy import deepcopy
from functools import wraps

import numpy as np
import pretty_midi
import scipy.io

from . import utils


def convert(exts, no_dot=True, remove_player=False):
    """
    This function that is designed to be used as decorators for functions which
    converts from a filetype to our JSON format.

    Example of usage:

    >>> @convert(['.myext'], no_dot=True, remove_player=False)
    ... def function_which_converts(...):
    ...     pass

    Parameters
    ---
    * ext : list of str
        the possible extensions of the ground-truths to be converted, e.g.
        ['.mid', '.midi']. You can also use this parameter to remove exceeding
        parts at the end of the filename (see `from_bach10_mat` and
        `from_bach10_f0` source code)

    * no_dot : boolean
        if True, don't add a dot before of the extension, if False, add it
        if not present; this is useful if you are using the extension to remove
        other parts in the file name (see `ext`).

    * remove_player : boolean
        if True, remove the name of the player in the last part of the file
        name: use this for the `traditional_flute` dataset; it will remove the
        part after the last '_'.
    """
    def _convert(user_convert):
        @wraps(user_convert)
        def func(input_fn, *args, **kwargs):
            for ext in exts:
                new_fn = change_ext(input_fn, ext, no_dot, remove_player)
                if os.path.exists(new_fn):
                    break

            out = user_convert(new_fn, *args, **kwargs)

            if type(out) is dict:
                out = [out]
            return out

        return func

    return _convert


prototype_gt = {
    "precise_alignment": {
        "onsets": [],
        "offsets": [],
        "pitches": [],
        "notes": [],
        "velocities": []
    },
    "misaligned": {
        "onsets": [],
        "offsets": [],
        "pitches": [],
        "notes": [],
        "velocities": []
    },
    "score": {
        "onsets": [],
        "offsets": [],
        "pitches": [],
        "notes": [],
        "velocities": [],
        "beats": []
    },
    "broad_alignment": {
        "onsets": [],
        "offsets": [],
        "pitches": [],
        "notes": [],
        "velocities": []
    },
    "f0": [],
    "soft": {
        "values": [],
        "times": []
    },
    "sostenuto": {
        "values": [],
        "times": []
    },
    "sustain": {
        "values": [],
        "times": []
    },
    "instrument": 255,
}
"""
The dictionary prototype for containing the ground_truth.
use:

>>> from copy import deepcopy
... from convert_from_file import prototype_gt
... prototype_gt = deepcopy(prototype_gt)

>>> prototype_gt
{
    "precise_alignment": {
        "onsets": [],
        "offsets": [],
        "pitches": [],
        "notes": [],
        "velocities": []
    },
    "misaligned": {
        "onsets": [],
        "offsets": [],
        "pitches": [],
        "notes": [],
        "velocities": []
    },
    "score": {
        "onsets": [],
        "offsets": [],
        "pitches": [],
        "notes": [],
        "velocities": [],
        "beats": []
    },
    "broad_alignment": {
        "onsets": [],
        "offsets": [],
        "pitches": [],
        "notes": [],
        "velocities": []
    },
    "f0": [],
    "soft": {
        "values": [],
        "times": []
    },
    "sostenuto": {
        "values": [],
        "times": []
    },
    "sustain": {
        "values": [],
        "times": []
    },
    "instrument": 255,
}

Note: ``pitches``, ``velocities``, ``sustain``, ``sostenuto``, ``soft``, and
(if available) ``instrument`` must be in range [0, 128)
"""


def change_ext(input_fn, new_ext, no_dot=False, remove_player=False):
    """
    Return the input path `input_fn` with `new_ext` as extension and the part
    after the last '-' removed.
    If `no_dot` is True, it will not add a dot before of the extension,
    otherwise it will add it if not present.
    `remove_player` can be used to remove the name of the player in the last
    part of the file name when: use this for the `traditional_flute` dataset;
    it will remove the last part after '_'.
    """

    root = input_fn[:input_fn.rfind('-')]
    if remove_player:
        root = root[:root.rfind('_')]
    if not new_ext.startswith('.'):
        if not no_dot:
            new_ext = '.' + new_ext

    return root + new_ext


def from_midi(midi_fn,
              alignment='precise_alignment',
              pitches=True,
              velocities=True,
              merge=True,
              beats=False):
    """
    Open a midi file `midi_fn` and convert it to our ground_truth
    representation. This fills velocities, pitches, beats, sustain, soft,
    sostenuto and alignment (default: `precise_alignment`). Returns a list
    containing a dictionary. `alignment` can also be `None` or `False`, in that
    case no alignment is filled. If `merge` is True, the returned list will
    contain a dictionary for each track.  Beats are filled according to tempo
    changes.

    This functions is decorated with two different sets of parameters:

    * `from_midi` is the decorated version with `remove_player=False`
    * `from_midi_remove_player` is the decorated version with `remove_player=True`
    """
    midi_tracks, pm = utils.open_midi(midi_fn, merge=merge, pm_object=True)

    out = list()

    if merge:
        midi_tracks = [midi_tracks]

    for i, track in enumerate(midi_tracks):
        data = deepcopy(prototype_gt)
        for cc in pm.instruments[i].control_changes:
            if cc.number == 64:
                data['sustain']['values'].append(cc.value)
                data['sustain']['times'].append(cc.time)
            elif cc.number == 66:
                data['sostenuto']['values'].append(cc.value)
                data['sostenuto']['times'].append(cc.time)
            elif cc.number == 67:
                data['soft']['values'].append(cc.value)
                data['soft']['times'].append(cc.time)

        for note_group in track:
            for note in note_group:
                if pitches:
                    data[alignment]["pitches"].append(note.pitch)
                if velocities:
                    data[alignment]["velocities"].append(note.velocity)
                if alignment:
                    data[alignment]["onsets"].append(
                        float(note.start))
                    data[alignment]["offsets"].append(
                        float(note.end))
                if beats and alignment == 'score':
                    data[alignment]["beats"] = pm.get_beats().tolist()
        out.append(data)

    return out


from_midi_remove_player = convert(['.mid', '.midi'],
                                  remove_player=True)(from_midi)
from_midi = convert(['.mid', '.midi'], remove_player=False)(from_midi)


@convert(['.txt'])
def from_phenicx_txt(txt_fn):
    """
    Open a txt file `txt_fn` in the PHENICX format and convert it to our
    ground_truth representation. This fills: `broad_alignment`.
    """
    out_list = list()

    with open(txt_fn) as f:
        lines = f.readlines()

    out = deepcopy(prototype_gt)
    for line in lines:
        fields = re.split(',|\n', line)
        out["broad_alignment"]["notes"].append(fields[2])
        out["broad_alignment"]["pitches"].append(
            pretty_midi.note_name_to_number(fields[2]))
        out["broad_alignment"]["onsets"].append(float(fields[0]))
        out["broad_alignment"]["offsets"].append(float(fields[1]))
    out_list.append(out)

    return out_list


@convert(['-GTNotes.mat'], no_dot=True)
def from_bach10_mat(mat_fn, sources=range(4)):
    """
    Open a txt file `txt_fn` in the MIREX format (Bach10) and convert it to
    our ground_truth representation. This fills: `precise_alignment`, `pitches`.
    `sources` is an iterable containing the indices of the  sources to be
    considered, where the first source is 0. Returns a list of dictionary, one
    per source.
    """
    out_list = list()

    mat = scipy.io.loadmat(mat_fn)['GTNotes']
    for i in range(len(mat)):
        out = deepcopy(prototype_gt)
        source = mat[i, 0]
        for j in range(len(source)):
            note = source[j, 0]
            out["precise_alignment"]["pitches"].append(
                np.median(np.rint(note[1, :])))
            out["precise_alignment"]["onsets"].append(
                (note[0, 0] - 2) * 10 / 1000.)
            out["precise_alignment"]["offsets"].append(
                (note[0, -1] - 2) * 10 / 1000.)
        out_list.append(out)

    return out_list


@convert(['-GTF0s.mat'], no_dot=True)
def from_bach10_f0(nmat_fn, sources=range(4)):
    """
    Open a matlab mat file `nmat_fn` in the MIREX format (Bach10) for frame
    evaluation and convert it to our ground_truth representation. This fills:
    `f0`.  `sources` is an iterable containing the indices of the  sources to
    be considered, where the first source is 0.  Returns a list of dictionary,
    one per source.
    """
    out_list = list()

    f0s = scipy.io.loadmat(nmat_fn)['GTF0s']
    for source in sources:
        out = deepcopy(prototype_gt)
        out["f0"] = f0s[source].tolist()
        out_list.append(out)

    return out_list


@convert(['.csv'])
def from_musicnet_csv(csv_fn, sr=44100.0):
    """
    Open a csv file `csv_fn` and convert it to our ground_truth representation.
    This fills: `broad_alignment`, `score`, `pitches`.
    This returns a list containing only one dict. `sr` is the samplerate of the
    audio files (MusicNet csv contains the sample number as onset and offsets of
    each note) and it shold be a float.

    N.B. MusicNet contains wav files at 44100 Hz as samplerate.
    N.B. Lowest in pitch in musicnet is 21, so we assume that they count pitch
    starting with 0 as in midi.org standard.
    N.B. `score` times are provided with BPM 60 for all the scores
    """
    data = csv.reader(open(csv_fn), delimiter=',')
    out = deepcopy(prototype_gt)

    # skipping first line
    next(data)

    for row in data:
        # converting everything to float, except the last onw that is the
        # duration name as string
        row = list(map(float, row[:-1]))

        out["broad_alignment"]["onsets"].append(int(row[0]) / sr)
        out["broad_alignment"]["offsets"].append(int(row[1]) / sr)
        out["instrument"] = int(row[2])
        out["broad_alignment"]["pitches"].append(int(row[3]))
        out["score"]["pitches"].append(int(row[3]))
        out["score"]["onsets"].append(float(row[4]))
        out["score"]["offsets"].append(
            float(row[4]) + float(row[5]))

        out["score"]["beats"] = [
            i for i in range(int(max(out["score"]["offsets"])) + 1)
        ]
    return out


@convert(['.gt'])
def from_sonic_visualizer(gt_fn, alignment='precise_alignment'):
    """
    Takes a filename of a sonic visualizer output file  exported as 'csv' and fills the
    'alignment' specified
    """

    data = csv.reader(open(gt_fn), delimiter=',')
    out = deepcopy(prototype_gt)
    for row in data:
        out[alignment]["onsets"].append(float(row[0]))
        out[alignment]["offsets"].append(float(row[0]) + float(row[2]))
        p = float(row[1])
        if p == 0:
            p += 1
        pitch = utils.f0_to_midi_pitch(p)
        out[alignment]["pitches"].append(pitch)

    return out
