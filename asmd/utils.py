import pathlib
from typing import Union, Tuple
import numpy as np
from essentia.standard import EasyLoader as Loader
from essentia.standard import MetadataReader


def nframes(dur, hop_size=3072, win_len=4096) -> float:
    """
    Compute the numbero of frames given a total duration, the hop size and
    window length. Output unitiy of measure will be the same as the inputs
    unity of measure (e.g. samples or seconds).

    N.B. This returns a float!
    """
    return (dur - win_len) / hop_size + 1


def frame2time(frame: int, hop_size=3072, win_len=4096) -> float:
    """
    Takes frame index (int) and returns the corresponding central sample
    The output will use the same unity of measure as ``hop_size`` and
    ``win_len`` (e.g. samples or seconds).
    Indices start from 0.

    Returns a float!
    """
    return frame * hop_size + win_len / 2


def time2frame(time, hop_size=3072, win_len=4096) -> int:
    """
    Takes a time position and outputs the best frame representing it.
    The input must use the same unity of measure for ``time``, ``hop_size``,
    and ``win_len`` (e.g. samples or seconds).  Indices start from 0.

    Returns and int!
    """
    return round((time - win_len / 2) / hop_size)


def open_audio(audio_fn: Union[str, pathlib.Path]) -> Tuple[np.ndarray, int]:
    """
    Open the audio file in `audio_fn` and returns a numpy array containing it,
    one row for each channel (only Mono supported for now) and the orginal
    sample_rate
    """

    reader = MetadataReader(filename=str(audio_fn), filterMetadata=True)
    sample_rate = reader()[-2]
    if sample_rate == 0:
        raise RuntimeError("No sample rate metadata in file " + str(audio_fn))

    loader = Loader(filename=str(audio_fn),
                    sampleRate=sample_rate,
                    endTime=1e+07)
    return loader(), sample_rate


def open_midi(midi_fn,
              considered_tracks=slice(None),
              merge=True,
              pm_object=False):
    """
    Open file `midi_fn` and returns a list of `pretty_midi.Note` existing in
    `considered_tracks`. The output list contains lists, each one containingh:
    notes with the same onset time. `considered_tracks` can also be an `int`.
    If `merge` is True, all `considered_tracks` are merged into one, otherwise
    a list of tracks will be returned. If `pm` is True, the original
    PrettyMidi object will also be returned.
    """
    import pretty_midi as pm
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


def f0_to_midi_pitch(f0):
    """
    Return a midi pitch (in 0-127) given a frequency value in Hz
    """
    return 12 * np.log2(f0 / 440) + 69


def midi_pitch_to_f0(midi_pitch):
    """
    Return a frequency given a midi pitch (in 0-127)
    """
    return 440 * 2**((midi_pitch - 69) / 12)
