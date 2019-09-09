from .audioscoredataset import Dataset
import numpy as np
import plotly.graph_objects as go
import plotly.offline as plt


BIN_WIDTH = 0.0005
LENGTH = int(20*1/BIN_WIDTH)
data = Dataset('datasets/datasets.json')

def take_hist(alignment):
    data.filter(ground_truth=["non_aligned",alignment])

    ons_hist = np.zeros(LENGTH)
    offs_hist = np.zeros(LENGTH)
    for i in range(len(data)):
        mat_aligned = data.get_score(i, score_type=alignment)
        mat_score = data.get_score(i, score_type='non_aligned')
        try:
            ons_deviations = mat_score[:, 1] - mat_aligned[:, 1]
            offs_deviations = mat_score[:, 2] - mat_aligned[:, 2]
        except:
            import ipdb; ipdb.set_trace()

        for dev in ons_deviations:
            idx = compute_idx(dev)
            ons_hist[idx] += 1

        for dev in offs_deviations:
            idx = compute_idx(dev)
            offs_hist[idx] += 1

    return ons_hist, offs_hist

def compute_idx(dev):
    idx = int(dev / BIN_WIDTH) + LENGTH / 2
    if dev < 0:
        idx -= 1
    idx = max(0, idx)
    idx = min(LENGTH-1, idx)
    return int(idx)

ons_hist, offs_hist = take_hist('precise_alignment')
# _ons_hist, _offs_hist = take_hist('broad_alignment')

# ons_hist += _ons_hist
# offs_hist += _offs_hist

ons_hist /= np.sum(ons_hist)
offs_hist /= np.sum(offs_hist)
np.savez_compressed("histograms.npz", ons_hist=ons_hist, offs_hist=offs_hist)

fig1 = go.Figure(data=[go.Scatter(y=ons_hist)])
plt.plot(fig1, filename='ons.html')
fig2 = go.Figure(data=[go.Scatter(y=offs_hist)])
plt.plot(fig2, filename='offs.html')
