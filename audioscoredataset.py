#!/usr/bin/env python
import json
import gzip
from os.path import join as joinpath
from .utils import io
import numpy as np

class Dataset:

    def __init__(self, path):
        """
        Load the dataset description

        Parameters
        ----------
        path : str
            path of the `json` dataset file

        Returns
        -------
        AudioScoreDataset :
            instance of the class
        """
        self.data = json.load(open(path, 'rt'))
        self.install_dir = self.data['install_dir']
        self.decompress_path = './'
        self.paths = []

    def filter(self, instrument='', ensemble=False, mixed=True, sources=False, all=False, composer='', ground_truth=[]):
        """
        Filters the dataset and load the paths of the songs which accomplish
        the filter described in `kwargs`. A field `paths` is added to this
        instance.

        Arguments
        ---------
        instrument : str
            a string representing the instrument that you
            want to select (only one supported for now)
        ensemble : bool
            if loading songs which are composed for an ensemble of
            instrument (default  False )
        mixed : bool
            if returning the mixed track for ensemble song
            (default  True )
        sources : bool
            if returning the source track for ensemble recording
            which provide it (default  False )
        all : bool
            only valid if  sources  is  True : if  True , all
            sources (audio and ground-truth) are returned, if
            False , only the target instrument is returned. Default False.
        composer : string
            the surname of the composer to filter
        ground_truth : list of strings
            a list of strings representing the type of ground-truths needed
            (logical AND among list elements)
        """
        for mydataset in self.data['datasets']:
            FLAG = True;

            # checking dataset-level filters
            if ensemble != mydataset['ensemble']:
                FLAG = False

            if not instrument:
                if instrument not in mydataset['instruments']:
                    FLAG = False

            for gt in ground_truth:
                if not mydataset['ground_truth'][gt]:
                    FLAG = False
                    break

            if FLAG:
                for song in mydataset['songs']:
                    # checking song levels filters
                    if instrument:
                        if instrument not in song['instruments']:
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
                                idx = song['instruments'].index(instrument)

                                # take index of the target instrument
                                source = song['sources']['path'][idx]
                                gts = song['ground_truth'][idx]

                        if mixed:
                            mix = song['recording']['path']
                        self.paths.append([mix, source, gts])

    def get_mix(self, idx):
        """
        Returns the audio array of the mixed song

        Arguments
        ---------
        idx : int
            the index of the wanted item

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
            audio, sr = io.open_audio(joinpath(self.install_dir, recording_fn))
            recordings.append(audio)

        if len(recordings) > 1:
            mix = np.mean(recordings, axis=0)
        else:
            mix = recordings[0]
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
        gts_fn = self.paths[idx][2];
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
        list :
            a list of numpy.ndarray representing the audio of each source
        int :
            The sampling rate of the audio array
        """
        sources_fn = self.paths[idx][1]

        sources = []
        for source_fn in sources_fn:
            audio, sr = io.open_audio(joinpath(self.install_dir, source_fn))
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

    def get_score(self, idx, score_type='non_aligned'):
        """
        Get the score of a certain score, with times of `score_type`

        Arguments
        ---------
        idx : int
            The index of the song to retrieve.
        score_type : str
            The key to retrieve the list of notes from the ground_truths

        Returns
        -------
        numpy.ndarray :
            A (n x 6) array where columns represent pitches, onsets (seconds),
            offsets (seconds), velocities, MIDI program instrument and number of
            the instrument. Ordered by onsets. If some information is not
            available, value -255 is used.
        """

        print("    Loading ground truth")
        gts = self.get_gts(idx)
        mat = []
        for i, gt in enumerate(gts):
            # This is due to Bach10 datasets 
            diff_notes = 0
            if len(gt['pitches']) != len(gt[score_type]['onsets']):
                import wdb; wdb.set_trace()
                diff_notes = len(gt['pitches']) - len(gt[score_type]['onsets'])
                print('---- This file contains different data in '+score_type+' and number of pitches!')
                print('----', diff_notes, 'different notes')

            # initilize each column
            ons = gt[score_type]['onsets']
            if not ons:
                ons = np.full_like(gt['pitches'], -255)
            offs = gt[score_type]['offsets']
            if not offs:
                offs = np.full_like(ons, -255)
            pitches = gt['pitches']
            if diff_notes < 0:
                # not the best way to deal with this...
                ons = ons[:len(pitches)]
                offs = offs[:len(pitches)]
            elif diff_notes > 0:
                pitches = pitches[:len(ons)]

            vel = gt['velocities']
            if not vel:
                vel = np.full_like(ons, -255)
            num = np.full_like(ons, i)
            instr = np.full_like(ons, gt['instrument'])
            mat.append(np.array([pitches, ons, offs, vel, instr, num]))

        if len(mat) > 1:
            # mat now contains one list per each ground-truth, concatenating
            mat = np.concatenate(mat, axis=1)
        else:
            mat = np.array(mat)
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


