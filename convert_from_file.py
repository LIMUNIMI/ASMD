from copy import deepcopy
import os
import csv
import scipy.io
from utils import io
import re
import pretty_midi

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


def from_midi(midi_fn, alignment='precise_alignment', pitches=True, velocities=True, merge=True, remove_player=False):
    """
    Open a midi file `midi_fn` and convert it to our ground_truth
    representation. This fills velocities, pitches and alignment (default:
    `precise_alignment`). Returns a list containing a dictionary. `alignment`
    can also be `None` or `False`, in that case no alignment is filled. If `merge` is
    True, the returned list will contain a dictionary for each track.
    `remove_player` can be used to remove the name of the player in the last
    part of the file name when: use this for the `traditional_flute` dataset.
    """
    new_midi_fn = change_ext(midi_fn, '.mid', remove_player=remove_player)
    if not os.path.exists(new_midi_fn):
        new_midi_fn = change_ext(midi_fn, '.midi', remove_player=remove_player)

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
        fields = re.split(',|\n', line)
        out["notes"].append(fields[2])
        out["pitches"].append(pretty_midi.note_name_to_number(fields[2]))
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
                out["precise_alignment"]["onsets"].append(
                    float(fields[0]) / 1000.)
                out["precise_alignment"]["offsets"].append(
                    float(fields[1]) / 1000.)
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

    return [out]


#: a dictionary which maps each dataset to a set of functions
func_map = {
    'Bach10': [
        (from_bach10_f0, {}),
        (from_bach10_txt, {}),
        (from_midi,
         {
             'alignment': 'non_aligned',
             'pitches': False,
             'velocities': False,
             'merge': False
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
            'remove_player': True
        }),
        (from_sonic_visualizer, {})
    ],
    'vienna_corpus': [
        (from_midi, {
            'alignment': 'non_aligned',
            'pitches': True,
            'velocities': False,
            'merge': True,
            'remove_player': True
        }),
        (from_midi, {
            'alignment': 'precise_alignment',
            'pitches': False,
            'velocities': True,
            'merge': True,
            'remove_player': False
        })
    ]
}
