from random import choices, uniform
from sklearn.preprocessing import StandardScaler, minmax_scale
import numpy as np
import os.path
from .audioscoredataset import Dataset
from . import utils

data = Dataset()

THISDIR = os.path.dirname(os.path.realpath(__file__))


class Stats:
    def __init__(self):
        self.ons_diffs = []
        self.offs_diffs = []
        self.means = []
        self.ons_dev = []
        self.offs_dev = []

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

    def get_random_onset_dev(self, k=1, max_value=None):
        return _get_random_value_from_hist(self.ons_dev_hist,
                                           k,
                                           max_value=max_value)

    def get_random_offset_dev(self, k=1, max_value=None):
        return _get_random_value_from_hist(self.offs_dev_hist,
                                           k,
                                           max_value=max_value)

    def get_random_mean(self, k=1, max_value=None):
        return _get_random_value_from_hist(self.means_hist,
                                           k,
                                           max_value=max_value)

    def get_random_onset_diff(self, k=1, max_value=None):
        return _get_random_value_from_hist(self.ons_hist, k, max_value=None)

    def get_random_offset_diff(self, k=1, max_value=None):
        return _get_random_value_from_hist(self.offs_hist, k, max_value=None)


def seed():
    """
    Apply a seed to the python random module to reproduce my results
    """
    import random
    random.seed(1992)


def _get_random_value_from_hist(hist, k=1, max_value=None):
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
    return [uniform(start[i], end[i]) for i in range(len(start))]


def fill_stats(datasets):
    stats = Stats()

    for dataset_name, alignment_type in datasets:
        data.paths = []
        data.filter(datasets=[dataset_name])

        for i in range(len(data)):
            mat_aligned = data.get_score(i, score_type=[alignment_type])
            mat_score = data.get_score(i, score_type=['non_aligned'])
            # selecting only rows where mat scores have values > 0
            mat_aligned = mat_aligned[
                np.all(mat_aligned[:, [0, 1, 2]] >= 0, axis=1), :]
            mat_score = mat_score[np.all(mat_score[:,
                                                   [0, 1, 2]] >= 0, axis=1), :]
            mat_aligned[:, 0] = np.round(mat_aligned[:, 0])
            mat_score[:, 0] = np.round(mat_score[:, 0])
            ons_diffs, offs_diffs = utils.evaluate2d(mat_score, mat_aligned)
            stats.add_data(ons_diffs, offs_diffs)

    return stats


if __name__ == '__main__':
    import os
    import pickle
    import plotly.graph_objects as go
    import plotly.offline as plt
    stats = fill_stats([
        ('vienna_corpus', 'precise_alignment'),
        # ('PHENICX', 'broad_alignment'),
        ('Bach10', 'precise_alignment'),
        ('traditional_flute', 'precise_alignment')
    ])
    stats.compute_hist()
    seed()
    v1 = stats.get_random_onset_dev()
    v2 = stats.get_random_offset_dev()
    v3 = stats.get_random_mean()
    v4 = stats.get_random_offset_diff()
    v5 = stats.get_random_onset_diff()
    print("Testing getting random value")
    print(v1, v2, v3, v4, v5)

    file_stats = os.path.join(THISDIR, "_alignment_stats.pkl")
    if os.path.exists(file_stats):
        os.remove(file_stats)
    pickle.dump(stats, open(file_stats, 'wb'))

    fig1 = go.Figure(
        data=[go.Scatter(y=stats.ons_hist[0], x=stats.ons_hist[1])])
    plt.plot(fig1, filename='ons.html')
    fig2 = go.Figure(
        data=[go.Scatter(y=stats.offs_hist[0], x=stats.offs_hist[1])])
    plt.plot(fig2, filename='offs.html')
    fig3 = go.Figure(
        data=[go.Scatter(y=stats.means_hist[0], x=stats.means_hist[1])])
    plt.plot(fig3, filename='ons_means.html')
    fig5 = go.Figure(
        data=[go.Scatter(y=stats.ons_dev_hist[0], x=stats.ons_dev_hist[1])])
    plt.plot(fig5, filename='ons_devs.html')
    fig6 = go.Figure(
        data=[go.Scatter(y=stats.offs_dev_hist[0], x=stats.offs_dev_hist[1])])
    plt.plot(fig6, filename='offs_devs.html')
