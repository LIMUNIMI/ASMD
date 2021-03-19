import os
import os.path
import pickle
import random
from copy import deepcopy
from random import choices, uniform
from typing import List, Tuple

import numpy as np
from sklearn.preprocessing import StandardScaler, minmax_scale

from hmmlearn.hmm import GMMHMM

from .asmd import Dataset
from .dataset_utils import filter, get_score_mat, union
from .eita.alignment_eita import get_matching_notes
from .idiot import THISDIR
from .utils import mat_stretch

NJOBS = -1


# TODO: refactoring: most of the stuffs are repeated twice for onsets and offsets
class Stats(object):
    def __init__(self, ons_dev_max=0.2, offs_dev_max=0.2, mean_max=None):
        self.offs_diffs = []
        self.ons_diffs = []
        self.ons_lengths = []
        self.offs_lengths = []
        self.means = []
        self.ons_dev = []
        self.offs_dev = []
        self.ons_dev_max = ons_dev_max
        self.offs_dev_max = offs_dev_max
        self.mean_max = mean_max
        self._song_offset_dev = 1
        self._song_onset_dev = 1
        self._song_mean = 0
        self._seed = 1992

    def seed(self):
        """
        Calls `seed` on python `random` and then increments its own seed of one
        """
        random.seed(self._seed)
        self._seed += 1
        return self._seed

    def add_data_to_histograms(self, ons_diffs, offs_diffs):
        """
        Method to add data, then you should still compute histograms
        """
        self.ons_dev.append(np.std(ons_diffs))
        self.offs_dev.append(np.std(offs_diffs))
        self.means.append(np.mean([offs_diffs, ons_diffs]))

        self.ons_diffs += StandardScaler().fit_transform(
            ons_diffs.reshape(-1, 1)).tolist()
        self.offs_diffs += StandardScaler().fit_transform(
            offs_diffs.reshape(-1, 1)).tolist()

        self.ons_lengths.append(len(ons_diffs))
        self.offs_lengths.append(len(offs_diffs))

    def get_random_onset_dev(self, k=1):
        self.seed()
        return _get_random_value_from_hist(self.ons_dev_hist,
                                           k,
                                           max_value=self.ons_dev_max)

    def get_random_offset_dev(self, k=1):
        self.seed()
        return _get_random_value_from_hist(self.offs_dev_hist,
                                           k,
                                           max_value=self.offs_dev_max)

    def get_random_mean(self, k=1):
        self.seed()
        return _get_random_value_from_hist(self.means_hist,
                                           k,
                                           max_value=self.mean_max)

    def new_song(self):
        """
        Prepare this object for a new song
        """
        self.seed()
        self._song_offset_dev = self.get_random_offset_dev()
        self.seed()
        self._song_onset_dev = self.get_random_onset_dev()
        self.seed()
        self._song_mean = self.get_random_mean()

    def fill_stats(self, dataset: Dataset):
        """
        Fills this object with data from `datasets`
        """

        global process_

        def process_(i, dataset):
            try:
                score, aligned = get_matching_scores(dataset, i)
            except RuntimeError:
                # skipping if we cannot match the notes for this score
                return None

            # computing diffs
            ons_diffs = score[:, 1] - aligned[:, 1]
            offs_diffs = score[:, 2] - aligned[:, 2]
            return ons_diffs, offs_diffs

        # puts in `self._data` onset and offset diffs
        self._data = dataset.parallel(
            process_,  # type: ignore
            n_jobs=NJOBS,
            backend="multiprocessing")

        count = 0
        for res in self._data:
            if res is not None:
                count += 1
                ons_diffs, offs_diffs = res
                self.add_data_to_histograms(ons_diffs, offs_diffs)

        print(
            f"Using {count / len(self._data):.2f} songs ({count} / {len(self._data)})"
        )

    def get_random_offsets(self, aligned):
        self.seed()
        return self.get_random_offset_diff(
            len(aligned)) * self._song_offset_dev + aligned + self._song_mean

    def get_random_onsets(self, aligned):
        self.seed()
        return self.get_random_onset_diff(
            len(aligned)) * self._song_onset_dev + aligned + self._song_mean

    def get_random_onset_diff(self, k=1):
        pass

    def get_random_offset_diff(self, k=1):
        pass

    def train_on_filled_stats(self):
        """
        Compute all the histograms in tuples (histogram, bin_edges):
        self.means_hist
        self.ons_dev_hist
        self.offs_dev_hist
        """
        self.means_hist = np.histogram(self.means, bins='auto', density=True)
        self.ons_dev_hist = np.histogram(self.ons_dev,
                                         bins='auto',
                                         density=True)
        self.offs_dev_hist = np.histogram(self.offs_dev,
                                          bins='auto',
                                          density=True)


class HistStats(Stats):
    def __init__(self, ons_max=None, offs_max=None, stats: Stats = None):
        super().__init__()
        if stats:
            self.__dict__.update(deepcopy(stats.__dict__))
        self.ons_max = ons_max
        self.offs_max = offs_max

    def train_on_filled_stats(self):
        super().train_on_filled_stats()
        # computing onset and offset histograms
        self.ons_hist = np.histogram(self.ons_diffs, bins='auto', density=True)
        self.offs_hist = np.histogram(self.offs_diffs,
                                      bins='auto',
                                      density=True)

    def get_random_onset_diff(self, k=1):
        self.seed()
        return _get_random_value_from_hist(self.ons_hist,
                                           k,
                                           max_value=self.ons_max)

    def get_random_offset_diff(self, k=1):
        self.seed()
        return _get_random_value_from_hist(self.offs_hist,
                                           k,
                                           max_value=self.offs_max)

    def __repr__(self):
        return str(type(self))


class HMMStats(Stats):
    def __init__(self, stats: Stats = None):
        super().__init__()

        if stats:
            self.__dict__.update(deepcopy(stats.__dict__))

        n_mix = 30  # the number of gaussian mixtures
        n_components = 25  # the number of hidden states
        n_iter = 1000  # maximum number of iterations
        tol = 1e-5  # minimum value of log-likelyhood
        covariance_type = 'diag'
        self.onshmm = GMMHMM(
            n_components=n_components,
            n_mix=n_mix,
            covariance_type=covariance_type,
            n_iter=n_iter,
            tol=tol,
            # verbose=True,
            random_state=self.seed())
        self.offshmm = GMMHMM(
            n_components=n_components,
            n_mix=n_mix,
            covariance_type=covariance_type,
            n_iter=n_iter,
            tol=tol,
            # verbose=True,
            random_state=self.seed())

    def get_random_onset_diff(self, k=1):
        x, _state_seq = self.onshmm.sample(k, random_state=self.seed())
        return x[:, 0]

    def get_random_offset_diff(self, k=1):
        x, _state_seq = self.offshmm.sample(k, random_state=self.seed())
        return x[:, 0]

    def train_on_filled_stats(self):
        super().train_on_filled_stats()

        # train the hmms
        def train(hmm, data, lengths):
            hmm.fit(data, lengths)
            if (hmm.monitor_.converged):
                print("hmm converged!")
            else:
                print("hmm did not converge!")

        print("Training onset hmm...")
        train(self.onshmm, self.ons_diffs, self.ons_lengths)
        print("Training offset hmm...")
        train(self.offshmm, self.offs_diffs, self.offs_lengths)

    def __repr__(self):
        return str(type(self))


def get_matching_scores(dataset: Dataset,
                        i: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Get a sub-scores of matching notes between `score` and the mos precisely
    aligned data available for song at index `i`

    Returns aligned, score
    """
    mat_aligned = get_score_mat(
        dataset, i, score_type=['precise_alignment', 'broad_alignment'])
    mat_score = get_score_mat(dataset, i, score_type=['score'])

    # stretch to the same average BPM
    mat_stretch(mat_score, mat_aligned)

    # changing float pitches to nearest pitch
    mat_aligned[:, 0] = np.round(mat_aligned[:, 0])
    mat_score[:, 0] = np.round(mat_score[:, 0])

    # apply Eita method
    matching_notes = get_matching_notes(mat_score, mat_aligned, timeout=20)
    if matching_notes is None:
        raise RuntimeError("Cannot match notes for this score!")
    return mat_score[matching_notes[:, 0]], mat_aligned[matching_notes[:, 1]]


def _get_random_value_from_hist(hist, k=1, max_value=None, hmm=False):
    """
    Given a histogram (tuple returned by np.histogram), returns a random value
    picked with uniform distribution from a bin of the histogram. The bin is
    picked following the histogram distribution. If `max` is specified, the
    histogram is first normalized so that the maximum absolute value is the one
    specified.
    """
    if max_value:
        values = minmax_scale(hist[1], (-abs(max_value), abs(max_value)))
    else:
        values = hist[1]
    start = choices(values[:-1], weights=hist[0], k=k)
    bin_w = abs(values[1] - values[0])
    end = np.array(start) + bin_w
    return np.asarray([uniform(start[i], end[i]) for i in range(len(start))])


def evaluate(dataset: Dataset, stats: List[Stats], onsoffs: str):
    """
    Computes classical DTW over all datasets and returns avarage and standard
    deviation of all the DTW distances for each `Stats` object in stats

    This function will also need to install the dtw-python module separately
    """
    global process_

    def process_(i: int, dataset: Dataset, stat: Stats):
        try:
            from dtw import dtw  # noqa: autoimport
        except ImportError:
            print(
                "Please install dtw-python by yourself before of running this function"
            )

        # reset the stats for a new song
        stat.new_song()

        try:
            # take the matching notes in the score
            score, aligned = get_matching_scores(dataset, i)
        except RuntimeError:
            # skipping if cannot match notes
            return -1

        # take random standardized differences
        if onsoffs == 'ons':
            aligned_diff = stat.get_random_onset_diff(k=score.shape[0])
            col = 1
        else:
            aligned_diff = stat.get_random_offset_diff(k=score.shape[0])
            col = 2

        # computing meang and dev from the matching notes
        diff = score[:, col] - aligned[:, col]
        mean = np.mean(diff)
        std = np.std(diff)

        # DTW between score and affinely transformed new times
        dtw_res = dtw(
            score[:, col],
            aligned[:, col] + aligned_diff * std + mean,
            # window_type='slantedband',
            # window_args=dict(window_size=10),
            distance_only=True)
        return dtw_res.normalizedDistance

    for stat in stats:
        print(f"Evaluating {stat}")
        distances = dataset.parallel(
            process_,  # type: ignore
            stat,
            n_jobs=NJOBS,
            backend="multiprocessing")
        # removing scores where we couldn't match notes
        distances = np.asarray(distances)
        distances = distances[distances >= 0]
        print(f"Statics for {stat} and {onsoffs}")
        print(f"Avg: {np.mean(distances):.2e}")
        print(f"Std {np.std(distances):.2e}")


def get_stats(method='histogram', save=True):
    """
    Computes statistics, histogram, dumps the object to file and returns it
    """
    dataset = _get_dataset()
    print("Computing statistics")
    stats = Stats()
    stats.fill_stats(dataset)
    return _train_model(stats, method, save)


def _get_dataset():
    dataset = Dataset()
    # dataset = filter(dataset,
    #                  datasets=['Bach10', 'traditional_flute', 'MusicNet'],
    #                  copy=True)

    dataset = union(
        filter(dataset,
               datasets=[
                   'vienna_corpus', 'Bach10', 'traditional_flute', 'MusicNet'
               ],
               copy=True),
        filter(dataset, datasets=['Maestro'], groups=['asap'], copy=True))
    return dataset


def _train_model(stats: Stats, method: str, save: bool):

    if method == 'histogram':
        stats = HistStats(stats=stats)
    elif method == 'hmm':
        stats = HMMStats(stats=stats)

    stats.train_on_filled_stats()

    if save:
        print("Saving statistical model")
        file_stats = os.path.join(THISDIR, "_alignment_stats.pkl")
        if os.path.exists(file_stats):
            os.remove(file_stats)
        pickle.dump(stats, open(file_stats, 'wb'))
    return stats


if __name__ == '__main__':
    dataset = _get_dataset()
    print("Computing statistics")
    stats = Stats()
    stats.fill_stats(dataset)

    for method in ['hmm', 'histogram']:
        stats = _train_model(stats, method, False)
        # stat = pickle.load(
        #     open(os.path.join(THISDIR, "_alignment_stats.pkl"), "rb"))
        evaluate(dataset, [
            stats,
        ], 'ons')
        evaluate(dataset, [
            stats,
        ], 'offs')
