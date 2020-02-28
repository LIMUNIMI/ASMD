# cython: language_level=3
import numpy as np
import pretty_midi as pm
from essentia.standard import EasyLoader as Loader
from essentia.standard import MetadataReader


def open_audio(audio_fn):
    """
    Open the audio file in `audio_fn` and returns a numpy array containing it,
    one row for each channel. (only Mono supported for now)
    """

    reader = MetadataReader(filename=str(audio_fn), filterMetadata=True)
    sample_rate = reader()[-2]

    loader = Loader(filename=str(audio_fn), sampleRate=sample_rate, endTime=1e+07)
    return loader(), sample_rate


def open_midi(midi_fn, considered_tracks=slice(None), merge=True, pm_object=False):
    """
    Open file `midi_fn` and returns a list of `pretty_midi.Note` existing in
    `considered_tracks`. The output list contains lists, each one containingh:
    notes with the same onset time. `considered_tracks` can also be an `int`.
    If `merge` is True, all `considered_tracks` are merged into one, otherwise
    a list of tracks will be returned. If `pm` is True, the original
    PrettyMidi object will also be returned.
    """
    midi_multitrack = pm.PrettyMIDI(midi_fn)

    if type(considered_tracks) is int:
        considered_tracks = slice(considered_tracks, considered_tracks + 1)

    tracks = []
    for track in midi_multitrack.instruments[considered_tracks]:
        if merge:
            tracks += track.notes
        else:
            tracks.append(track.notes)

    if merge:
        tracks = group_notes_by_onest(tracks)
    else:
        for i, notes in enumerate(tracks):
            tracks[i] = group_notes_by_onest(notes)

    if pm_object:
        return tracks, midi_multitrack
    else:
        return tracks


def group_notes_by_onest(notes):
    """
    Return a new list which contains lists of notes with the same onset,
    ordered in ascending order.
    """
    output = []
    notes.sort(key=lambda x: x.start)
    last_onset = notes[0].start
    inner_list = [notes[0]]
    for n in notes[1:]:
        if n.start == last_onset:
            inner_list.append(n)
        else:
            output.append(inner_list)
            inner_list = [n]
            last_onset = n.start
    return output

def evaluate2d(estimate, ground_truth):
    """
    Evaluate two 2D arrays in which rows are notes and columns are `pitch`, `onset` and `offset`.

    This function first compare the number of notes in the two arrays for all the pitches and
    removes notes in excess, so that the two arrays have the same number of pitches.
    Then, it returns two arrays with onsets and offsets relative errors,
    computed as `estimate - ground_truth` for all correspondend pitches, after
    having sorted by pitch and onset. Ordering is performed so that the input
    arrays don't need to be ordered in the same way.


    Arguments
    ---

    `estimate` : np.array
        The array of estimated timings. 2D array where rows are notes and
        columns are `pitch`, `onsets`, `offsets`

    `ground_truth` : np.array
        The array of ground_truth timings. 2D array where rows are notes and
        columns are `pitch`, `onsets`, `offsets`

    Returns
    ---

    `np.array` :
        A 1D array where the i element is the relative error computed as
        for the `i`-th estimated note onset, after having removed mismatching
        notes and having ordered by pitch and onset. Ordering is performed so that
        the input arrays don't need to be ordered in the same way.


    `np.array` :
        Same as the first output but for offsets.
    """
    ###########
    # removing last k pitches that create mismatch
    # after this operation all the pitches have the same cardinality in both lists
    pitches_est = np.unique(estimate[:, 0])
    pitches_gt = np.unique(ground_truth[:, 0])
    pitches = np.union1d(pitches_est, pitches_gt)
    for pitch in pitches:
        # computing how many notes for this pitch there are in estimate and ground_truth
        pitch_est = np.count_nonzero(estimate[:, 0] == pitch)
        pitch_gt = np.count_nonzero(ground_truth[:, 0] == pitch)

        # deciding from which we should remove notes of this pitch
        if pitch_est > pitch_gt:
            remove_from, not_remove_from = estimate, ground_truth
            pitch_not_remove_from = pitch_gt
        elif pitch_est < pitch_gt:
            remove_from, not_remove_from = ground_truth, estimate
            pitch_not_remove_from = pitch_est
        else:
            continue

        # taking indices of notes with this pitch in remove_from that are not in not_remove_from
        remove_from_idx = np.where(remove_from[:, 0] == pitch)[
            0][pitch_not_remove_from:]

        # remove from remove_from
        remove_from = np.delete(remove_from, remove_from_idx, 0)

        # reassigning names
        if pitch_est > pitch_gt:
            estimate, ground_truth = remove_from, not_remove_from
        elif pitch_est < pitch_gt:
            ground_truth, estimate = remove_from, not_remove_from

    ###########
    # sorting according to pitches and then onsets
    est_sorted = np.lexsort((estimate[:, 1], estimate[:, 0]))
    gt_sorted = np.lexsort((ground_truth[:, 1], ground_truth[:, 0]))

    # computing errors
    _err_ons = estimate[est_sorted, 1] - ground_truth[gt_sorted, 1]
    _err_offs = estimate[est_sorted, 2] - ground_truth[gt_sorted, 2]

    # sorting errors according to input
    err_ons = np.empty_like(_err_ons)
    err_offs = np.empty_like(_err_offs)
    err_ons[est_sorted] = _err_ons
    err_offs[est_sorted] = _err_offs

    return err_ons, err_offs


def f0_to_midi_pitch(f0):
    """
    Return a midi pitch given a frequency value in Hz
    """
    return 12*np.log2(f0 / 440)+69


def midi_pitch_to_f0(midi_pitch):
    """
    Return a frequency given a midi pitch
    """
    return 440 * 2**((midi_pitch-69)/12)
