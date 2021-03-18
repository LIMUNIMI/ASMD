import os
import os.path
import pickle
import random
from random import choices, uniform
from typing import List, Tuple

import numpy as np
from sklearn.preprocessing import StandardScaler, minmax_scale

from .asmd import Dataset
from .dataset_utils import filter, get_score_mat, union
from .eita.alignment_eita import get_matching_notes
from .idiot import THISDIR


class Stats(object):
    def __init__(self, ons_dev_max=0.2, offs_dev_max=0.2, mean_max=None):
        self.ons_diffs = []
        self.offs_diffs = []
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

    def add_data(self, ons_diffs, offs_diffs):
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

    def compute_hist(self):
        """
        Compute all the histograms in tuples (histogram, bin_edges):
        self.ons_hist
        self.offs_hist
        self.means_hist
        self.ons_dev_hist
        self.offs_dev_hist
        """
        self.ons_hist = np.histogram(self.ons_diffs, bins='auto', density=True)
        self.offs_hist = np.histogram(self.offs_diffs,
                                      bins='auto',
                                      density=True)
        self.means_hist = np.histogram(self.means, bins='auto', density=True)
        self.ons_dev_hist = np.histogram(self.ons_dev,
                                         bins='auto',
                                         density=True)
        self.offs_dev_hist = np.histogram(self.offs_dev,
                                          bins='auto',
                                          density=True)

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

    def get_random_onset_diff(self, k=1):
        pass

    def get_random_offset_diff(self, k=1):
        pass

    def get_random_onsets(self, aligned):
        pass

    def get_random_offsets(self, aligned):
        pass

    def fill_stats(self, dataset: Dataset):
        pass


class HistStats(Stats):
    def __init__(
        self,
        ons_max=None,
        offs_max=None,
    ):
        super().__init__()
        self.ons_max = ons_max
        self.offs_max = offs_max

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

    def get_random_offsets(self, aligned):
        self.seed()
        return _get_random_value_from_hist(
            self.offs_hist, len(aligned), max_value=self.offs_max
        ) * self._song_offset_dev + aligned + self._song_mean

    def get_random_onsets(self, aligned):
        self.seed()
        return _get_random_value_from_hist(
            self.ons_hist, len(aligned), max_value=self.ons_max
        ) * self._song_onset_dev + aligned + self._song_mean

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

        data = dataset.parallel(
            process_,  # type: ignore
            n_jobs=-1,
            backend="multiprocessing")
        count = 0
        for res in data:
            if res is not None:
                count += 1
                ons_diffs, offs_diffs = res
                self.add_data(ons_diffs, offs_diffs)

        print(f"Using {count / len(data):.2f} songs ({count} / {len(data)})")

    def __repr__(self):
        return str(type(self))


class HMMStats(Stats):
    def __init__(self):
        super().__init__()

    def get_random_onset_diff(self, k=1):
        raise NotImplementedError()

    def get_random_offset_diff(self, k=1):
        raise NotImplementedError()

    def fill_stats(self, dataset: Dataset):
        raise NotImplementedError()

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

    # changing float pitches to nearest pitch
    mat_aligned[:, 0] = np.round(mat_aligned[:, 0])
    mat_score[:, 0] = np.round(mat_score[:, 0])

    # apply Eita method
    matching_notes = get_matching_notes(mat_score, mat_aligned, timeout=None)
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
            n_jobs=-1,
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
    return _get_stats_from_dataset(_get_dataset(), method, save)


def _get_dataset():
    dataset = Dataset()
    # dataset = filter(
    #     dataset,
    #     datasets=['vienna_corpus', 'Bach10', 'traditional_flute', 'MusicNet'],
    #     copy=True)

    dataset = union(
        filter(dataset,
               datasets=[
                   'vienna_corpus', 'Bach10', 'traditional_flute', 'MusicNet'
               ],
               copy=True),
        filter(dataset, datasets=['Maestro'], groups=['asap'], copy=True))
    return dataset


def _get_stats_from_dataset(dataset: Dataset, method: str, save: bool):

    if method == 'histogram':
        stats: Stats = HistStats()
    elif method == 'hmm':
        stats = HMMStats()
    print("Computing statistics")
    stats.fill_stats(dataset)
    stats.compute_hist()

    print("Saving statistical model")
    if save:
        file_stats = os.path.join(THISDIR, "_alignment_stats.pkl")
        if os.path.exists(file_stats):
            os.remove(file_stats)
        pickle.dump(stats, open(file_stats, 'wb'))
    return stats


if __name__ == '__main__':
    dataset = _get_dataset()
    stat = _get_stats_from_dataset(dataset, 'histogram', False)
    # stat = pickle.load(
    #     open(os.path.join(THISDIR, "_alignment_stats.pkl"), "rb"))
    evaluate(dataset, [
        stat,
    ], 'ons')
    evaluate(dataset, [
        stat,
    ], 'offs')
