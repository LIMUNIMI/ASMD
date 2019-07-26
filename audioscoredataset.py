#!/usr/bin/env python3
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
                if gt not in mydataset['ground_truth']:
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
                        gts = song['ground-truth']
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
        """
        recordings_fn = self.paths[idx][0]

        recordings = []
        for recording_fn in recordings_fn:
            recordings.append(io.open_audio(joinpath(self.install_dir, recording_fn)))

        if len(recordings) > 1:
            mix = np.mean(recordings, axis=0)
        else:
            mix = recordings[0]
        return mix

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
        """
        sources_fn = self.paths[idx][1]

        sources = []
        for source_fn in sources_fn:
            sources.append(io.open_audio(joinpath(self.install_dir, source_fn)))
        return sources

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
