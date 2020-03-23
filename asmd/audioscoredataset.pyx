# cython: language_level=3
import json
import gzip
import os
import numpy as np
from joblib import Parallel, delayed
from . import utils
from os.path import join as joinpath
from essentia.standard import Resample
# this only for detecting package directory but breaks readthedocs
from .idiot import THISDIR
# THISDIR = './datasets/'


class Dataset:

    def __len__(self):
        return len(self.paths)

    def __init__(self, paths=[joinpath(THISDIR, 'definitions/')], metadataset_path=joinpath(THISDIR, 'datasets.json'), empty=False):
        """
        Load the dataset description

        Parameters
        ----------

        * paths : list of str
            paths where `json` dataset definitions are stored; if empty, the
            default definitions are used

        * metadataset_path : str
            the path were the generic information about where this datetimeis
            installed are stored

        * empty : bool
            if True, no definition is loaded

        Returns
        -------
        * AudioScoreDataset :
            instance of the class
        """

        self.datasets = []
        if not empty:
            if len(paths) == 0:
                paths = [joinpath(THISDIR, 'definitions/')]
            for path in paths:
                self.datasets += load_definitions(path)

        # opening medataset json file
        self.metadataset = json.load(open(metadataset_path, 'rt'))
        self.install_dir = self.metadataset['install_dir']
        if self.install_dir.endswith('/'):
            # this shouldn't happen actually...
            self.install_dir = self.install_dir[:-1]

        self.decompress_path = self.metadataset['decompress_path']
        self.paths = []
        self._chunks = {}


    def parallel(self, func, n_jobs=-2):
        """
        Applies a function to all items in `paths` in parallel using `joblib.Parallel`.

        Arguments
        ---------
        func : callable
            the function that will be called; it must accept two arguments
            that are the index of the song and the dataset. `filter` and
            `chunks` shouldn't be used

        n_jobs : int
            see `joblib.Parallel`

        Returns
        -------
        list:
            The list of objects returned by each `func`
        """

        return Parallel(n_jobs, backend="multiprocessing")(
            delayed(func_wrapper)(func, self.paths[i]) for i in range(len(self.paths)))


    def filter(self, instruments='', ensemble=None, mixed=True, sources=False, all=False, composer='', datasets=[], ground_truth=[]):
        """
        Filters the dataset and load the paths of the songs which accomplish
        the filter described in `kwargs`. A field `paths` is added to this
        instance.

        Arguments
        ---------
        instruments : list of str
            a list of strings representing the instruments that you
            want to select (exact match with song)
        ensemble : bool
            if loading songs which are composed for an ensemble of
            instrument. If None, ensemble field will not be checked and will
            select both (default None)
        mixed : bool
            if returning the mixed track for ensemble song
            (default  True )
        sources : bool
            if returning the source track for ensemble recording
            which provide it (default  False )
        all : bool
            only valid if  sources  is  True : if  True , all
            sources (audio and ground-truth) are returned, if
            False, only the first target instrument is returned. Default False.
        composer : string
            the surname of the composer to filter
        datasets : list of strings
            a list of strings containing the name of the datasets to be used.
            If empty, all datasets are used. See :doc:`License` for the
            list of default datasets.
        ground_truth : list of tuples
            a list of tuples representing the type of ground-truths needed
            (logical AND among list elements).
            Each tuple has the form `('needed_ground_truth_type',
            level_of_truth)`, where `needed_ground_truth_type` is the key of
            the ground_truth dictionary and `level_of_truth` is an int ranging
            from 0 to 2 (0->False, 1->True (manual annotation),
            2->True(automatic annotation))
        """
        end = 0
        for mydataset in self.datasets:
            FLAG = True
            if len(datasets) > 0:
                if mydataset['name'] in datasets:
                    FLAG = True
                else:
                    FLAG = False

            # checking dataset-level filters
            if ensemble is not None:
                if ensemble != mydataset['ensemble']:
                    FLAG = False

            for gt in ground_truth:
                if mydataset['ground_truth'][gt[0]] != gt[1]:
                    FLAG = False
                    break

            if FLAG:
                self._chunks[mydataset['name']] = [end, end]
                for song in mydataset['songs']:
                    FLAG = True
                    # checking song levels filters
                    if instruments:
                        if instruments != song['instruments']:
                            FLAG = False

                    if composer:
                        if composer not in song['composer']:
                            FLAG = False

                    if FLAG:
                        gts = song['ground_truth']
                        source = []
                        mix = []
                        if sources and "sources" in song.keys():
                            if all:
                                source = song['sources']['path']
                            else:
                                # find the index of the instrument
                                instrument = instruments[0]
                                idx = song['instruments'].index(instrument)

                                # take index of the target instrument
                                source = song['sources']['path'][idx]
                                gts = song['ground_truth'][idx]

                        if mixed:
                            mix = song['recording']['path']
                        self.paths.append([mix, source, gts])
                        end += 1
                self._chunks[mydataset['name']][1] = end


    def idx_chunk_to_whole(self, name, idx):
        """
        Given a dataset name and an idx or a list of idx relative to the input dataset,
        returns the idx relative to this whole dataset.
        """
        if type(idx) is int:
            return idx + self._chunks[name][0]
        elif type(idx) is list:
            return [i + self._chunks[name][0] for i in idx]
        else:
            raise Exception('idx should be int or list of int!')


    def get_mix(self, idx, sr=None):
        """
        Returns the audio array of the mixed song

        Arguments
        ---------
        idx : int
            the index of the wanted item
        sr : int or None
            the sampling rate at which the audio will be returned
            (if needed, a resampling is performed). If `None`, no
            resampling is performed

        Returns
        -------
        mix : numpy.ndarray
            the audio waveform of the mixed song
        int :
            The sampling rate of the audio array
        """
        recordings_fn = self.paths[idx][0]

        recordings = []
        for recording_fn in recordings_fn:
            audio, in_sr = utils.open_audio(
                joinpath(self.install_dir, recording_fn))
            recordings.append(audio)

        if len(recordings) > 1:
            mix = np.mean(recordings, axis=0)
        else:
            mix = recordings[0]

        if sr is not None:
            resampler = Resample(inputSampleRate=in_sr, outputSampleRate=sr)
            mix = resampler(mix)
        else:
            sr = in_sr
        return mix, sr

    def get_gts(self, idx):
        """
        Return the ground-truth of the wanted item

        Arguments
        ---------
        idx : int
            the index of the wanted item

        Returns
        -------
        list :
            list of dictionary representing the ground truth of each single source
        """

        gts = []
        gts_fn = self.paths[idx][2]
        for gt_fn in gts_fn:
            input_fn = joinpath(self.install_dir, gt_fn)

            gt = json.load(gzip.open(input_fn))
            gts.append(gt)
        return gts

    def get_source(self, idx):
        """
        Returns the sources at the specified index

        Arguments
        ---------
        idx : int
            the index of the wanted item

        Returns
        -------
        list :
            a list of numpy.ndarray representing the audio of each source
        int :
            The sampling rate of the audio array
        """
        sources_fn = self.paths[idx][1]

        sources = []
        for source_fn in sources_fn:
            audio, sr = utils.open_audio(joinpath(self.install_dir, source_fn))
            sources.append(audio)
        return sources, sr

    def get_item(self, idx):
        """
        Returns the mixed audio, sources and ground truths of the specified item.

        Arguments
        ---------
        idx : int
            the index of the wanted item

        Returns
        -------
        numpy.ndarray :
            audio of the mixed sources
        list :
            a list of numpy.ndarray representing the audio of each source
        list :
            list of dictionary representing the ground truth of each single source
        """
        mix = self.get_mix(idx)
        sources = self.get_source(idx)
        gts = self.get_gts(idx)
        return mix, sources, gts

    def get_pianoroll(self, idx, score_type=['non_aligned'], truncate=False, resolution=0.25):
        """
        Create pianoroll from list of pitches, onsets and offsets (in this order).

        Arguments
        ---------
        idx : int
            The index of the song to retrieve.
        score_type : list of str
            The key to retrieve the list of notes from the ground_truths. see
            `chose_score_type` for explanation
        truncate : bool
            If True, truncate mat to the shortest list among ons, offs and
            pitches, otherwise, insert -255 for missing values (enlarging
            lists)
        resolution : float
            The number of columns wanted per each second

        Returns
        -------
        numpy.ndarray :
            A (128 x n) array where rows represent pitches and columns are time
            instants sampled with resolution provided as argument. Values are
            the velocity of that note.
        """

        gts = self.get_gts(idx)
        score_type = chose_score_type(score_type, gts)

        # computing the maximum offset
        max_offs = [max(gt[score_type]['offsets']) for gt in gts]
        pianoroll = np.zeros((128, int(max(max_offs)/resolution) + 1))

        # filling pianoroll
        for i, gt in enumerate(gts):
            ons = gt[score_type]['onsets']
            offs = gt[score_type]['offsets']
            pitches = gt[score_type]['pitches']
            velocities = gt[score_type]['velocities']
            if not velocities:
                velocities = [1] * len(pitches)

            # Make pitches and alignments of thesame number of notes
            if truncate:
                find_bach10_errors(gt, score_type)
                truncate_score(gt)

            for i in range(len(pitches)):
                p = int(pitches[i])
                on = int(ons[i] / resolution)
                off = int(offs[i] / resolution) + 1

                pianoroll[p, on:off] = velocities[i]

        return pianoroll

    def get_beats(self, idx):
        """
        Get a list of beat position in seconds, to be used together with the
        non_aligned data.

        Arguments
        ---------
        idx : int
            The index of the song to retrieve.

        Returns
        -------
        numpy.ndarray :
            each row contains beat positions of each ground truth
        """
        gts = self.get_gts(idx)
        beats = []
        for gt in gts:
            beats.append(gt['beats_non_aligned'])

        return np.array(beats)

    def get_score(self, idx, score_type=['non_aligned'], truncate=False):
        """
        Get the score of a certain score, with times of `score_type`

        Arguments
        ---------
        idx : int
            The index of the song to retrieve.
        score_type : list of str
            The key to retrieve the list of notes from the ground_truths. see
            `chose_score_type` for explanation
        truncate : bool
            If True, truncate mat to the shortest list among ons, offs and
            pitches, otherwise, insert -255 for missing values (enlarging
            lists)

        Returns
        -------
        numpy.ndarray :
            A (n x 6) array where columns represent pitches, onsets (seconds),
            offsets (seconds), velocities, MIDI program instrument and number of
            the instrument. Ordered by onsets. If some information is not
            available, value -255 is used.
        """

        gts = self.get_gts(idx)
        score_type = chose_score_type(score_type, gts)

        # print("    Loading ground truth " + score_type)
        mat = []
        for i, gt in enumerate(gts):
            # Make pitches and alignments of thesame number of notes
            if truncate:
                find_bach10_errors(gt, score_type)
                truncate_score(gt)

            # initilize each column
            pitches = np.array(gt[score_type]['pitches'])

            ons = np.array(gt[score_type]['onsets'])
            if not len(ons):
                ons = np.full_like(pitches, -255)

            missing = len(pitches) - len(ons)
            if missing < 0:
                # add -255 to pitches
                pitches = np.append(pitches, [-255] * -missing)
            elif missing > 0:
                # add -255 to ons
                ons = np.append(ons, [-255] * missing)

            offs = np.append(gt[score_type]['offsets'], [-255] * missing)
            if not len(offs):
                offs = np.full_like(ons, -255)

            vel = np.append(gt[score_type]['velocities'], [-255] * missing)
            if not len(vel):
                vel = np.full_like(ons, -255)
            missing = len(pitches) - len(vel)
            if missing < 0:
                # add -255 to pitches, ons and offs
                pitches = np.append(pitches, [-255] * -missing)
                ons = np.append(ons, [-255] * -missing)
                offs = np.append(offs, [-255] * -missing)
            elif missing > 0:
                # add -255 to vel
                vel = np.append(vel, [-255] * missing)

            num = np.full_like(ons, i)
            instr = np.full_like(ons, gt['instrument'])
            mat.append(np.array([pitches, ons, offs, vel, instr, num]))

        if len(mat) > 1:
            # mat now contains one list per each ground-truth, concatenating
            mat = np.concatenate(mat, axis=1)
        else:
            mat = np.array(mat[0])
        # transposing: one row per note
        mat = mat.T
        # ordering by onset
        mat = mat[mat[:, 1].argsort()]
        return mat

    def get_audio(self, idx, sources=None):
        """
        Get the mixed audio of certain sources or of the mix

        Arguments
        ---------
        idx : int
            The index of the song to retrieve.
        sources : list or None
            A list containing the indices of sources to be mixed and returned.
            If `None`, no sources will be mixed and the global mix will be
            returned.

        Arguments
        ---------
        numpy.ndarray :
            A (n x 1) array which represents the mixed audio.
        int :
            The sampling rate of the audio array
        """

        print("    Loading audio")
        if sources is not None:
            audio, sr = self.get_source(idx)
            audio = np.mean(audio, axis=0)
        else:
            audio, sr = self.get_mix(idx)

        return audio, sr


def find_bach10_errors(gt, score_type):
    """
    Fix the ground-truth so that:
        - the extra notes in `score_type` are removed
        - the missing notes are inserted in middle of the last correct note,
          and the last correct note is halfed.

    NOTE
    ----
    NOTE IMPLEMENTED YET [probably never]. It only returns if there are errors
    and print the number of different notes between scores.

    Arguments
    ---------
    gt : dict
        the ground truth
    score_type : str
        the key to access the score to be fixed in the ground truth
        [non_aligned, broad_alignment, precise_alignment]

    Returns
    -------
    bool :
        if errors are detected
    """
    if len(gt[score_type]['pitches']) != len(gt[score_type]['onsets']):
        diff_notes = len(gt[score_type]['pitches']) - \
            len(gt[score_type]['onsets'])
        print('---- This file contains different data in ' +
              score_type+' and number of pitches!')
        print('----', diff_notes, 'different notes')
        return True
    return False


def truncate_score(gt):
    """
    Takes a ground truth and truncates all its lists so that the number of
    pitches is the same of the scoretype with the minimum number of pitches in
    this ground_truth
    """
    length_to_truncate = len(gt['non_aligned']['pitches'])
    score_types = ['non_aligned', 'precise_alignment', 'broad_alignment']

    # look for the length of the final lists
    for score_type in score_types:
        if len(gt[score_type]['onsets']) > 0:
            length_to_truncate = min(
                [len(gt[score_type]['onsets']), length_to_truncate, len(gt[score_type]['pitches'])])

    # truncating lists
    for score_type in score_types:
        gt[score_type]['pitches'] = gt[score_type]['pitches'][:length_to_truncate]
        gt[score_type]['velocities'] = gt[score_type]['velocities'][:length_to_truncate]
        gt[score_type]['onsets'] = gt[score_type]['onsets'][:length_to_truncate]
        gt[score_type]['offsets'] = gt[score_type]['offsets'][:length_to_truncate]


def load_definitions(path):
    """
    Given a `path` to a directory, returns a list of dictionaries containing
    the definitions found in that directory (not recursive search)
    """
    datasets = []
    for file in os.listdir(path):
        fullpath = joinpath(path, file)
        if os.path.isfile(fullpath) and fullpath.endswith('.json'):
            # add this dataset
            try:
                print("Opening " + fullpath)
                datasets.append(json.load(open(fullpath, 'rt')))
            except:
                print("Error opening " + fullpath)
    return datasets


def chose_score_type(score_type, gts):
    """
    Return the proper score type according to the following rules:

    Parameters
    ---

    score_type : list of str
        The key to retrieve the list of notes from the ground_truths. If
        multiple keys are provided, only one is retrieved by using the
        following criteria: if there is `precise_alignment` in the list of
        keys and in the ground truth, use that; otherwise, if there is
        `broad_alignment` in the list of keys and in the ground truth, use
        that; otherwise use `non_aligned`.

    gts : list of dict
        The list of ground truths from which you want to chose a score_type
    """
    if len(score_type) > 1:
        if 'precise_alignment' in score_type and len(gts[0]['precise_alignment']['pitches']) > 0:
            score_type = 'precise_alignment'
        elif 'broad_alignment' in score_type and len(gts[0]['broad_alignment']['pitches']) > 0:
            score_type = 'broad_alignment'
        else:
            score_type = 'non_aligned'
    else:
        score_type = score_type[0]
    return score_type


def func_wrapper(func, path):
    d = Dataset(empty=True)
    d.paths = [path]
    return func(0, d)
