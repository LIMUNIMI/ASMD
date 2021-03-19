Scientific notes
================

Artificial misalignment
-----------------------

This dataset tries to overcome the problem of needing manual alignment
of scores to audio for training models which exploit audio and scores at
the both time. The underlying idea is that we have many scores and a lot
of audio and users of trained models could easily take advantage of such
multimodality (the ability of the model to exploit both scores and
audio). The main problem is the annotation stage: we have quite a lot of
aligned data, but we miss the corresponding scores, and if we have the
scores, we almost always miss the aligned performance.

The approach used is to statistical analyze the available manual
annotations and to reproduce it. Indeed, with ``misaligned`` data I mean
data which try to reproduce the statistical features of the difference
between scores and aligned data.

Old description
~~~~~~~~~~~~~~~

For now, the statistical analysis is damn simple: I compute the mean and
the standard deviation of offsets and onsets for each piece. Then, I
take memory of the standardized histogram and of the histograms of means
and standard deviations. To create new misaligned data, I chose a
standardized value for each note and a mean and a standard deviation for
each piece, using the corresponding histograms; with these data, I can
compute a non-standardized value for each note. Note that the histograms
are first normalized so that they accomplish to given constraints. In
the present code, the standardized values are normalized to 1 (that is,
the maximum value is 1 second), while standard deviations are normalized
to 0.2 (see ``conversion_tool.py`` lines ``17-21``).

New description
~~~~~~~~~~~~~~~

You can evaluate the various approach by running ``python -m
asmd.alignment_stats``. The script will use Eita Nakamura method to match notes
between the score and the performance and will collect statistics only on the
matched notes; it will then compute the distance between the misaligned score
onset sequence and the real score onset sequence, considering only the matchng
notes, using the classical DTW symmetric step-pattern and the euclidean distance.
The evaluation uses `vienna_corpus`, `traditional_flute`, `MusicNet`, `Bach10`
and `asap` group from `Maestro` dataset for a total of 875 scores. However,
since Eita's method takes a long time on some scores, I removed the scores for
which Eita's method ends after 20 seconds; this resulted in a total of ~ 465
songs (~53% of the total number of songs with an available score).

Both the two compared methods are based on the random choice of a standard
deviation and a mean for the whole song according to the collected
distributions of standard deviations and means. They instead differ in how they
chose the standardized misalignment:

* old method randomly choses it according to the collected distribution
* new method uses an HMM with Gaussian mixture emissions instead of a simple
  distribution

Moreover, the misaligned data are computed with models trained on the stretched
scores, so that the training data consists of scores at the same average BPM as
the performance; the misaligned data, then, consists of times at the at that
average BPM.

The following table resumes the results of the comparison:

+------+-------------+-------------+
|      | Ons         | Offs        |
+------+-------------+-------------+
| HMM  | 6.63 ± 17.7 | 6.14 ± 20.5 |
+------+-------------+-------------+
| Hist | 8.97 ± 26.1 | 9.01 ± 26.2 |
+------+-------------+-------------+

Misaligned data are therefore more similar to a new performance than to a
symbolic score; for most of MIR applications, however, misaligned data are
enough for both training and evaluation.

BPM for `score` alignment
-------------------------

Previously, the BPM was always forced to 20, so that, if the BPM is not
available, notes duration can still be expressed in seconds. 

Since 0.4, the BPM is simply set to 60 if not available; however, positions of
beats are always provided, so that the user can reconstruct the instant BPM.
The function ``get_initial_bpm`` from the Python API also provides a way to
retrieve the initial instant BPM from the score.

An easy way to get an approximative BPM, is to `stretch` the score to the
duration of the corresponding performance. This can also be done for the beats,
and consequently, for the instant BPM. For instance, let `T_0` and `T_1` be the
initial and ending time of the performance, and let `t_0` and `t_1` be the initial
and ending times of the score. Then, the stretched times of the score at the
average performance BPM are given by:

`t_new = (t_old - t_0) * (T_1 - T_0) + T_0`

where `t_old` is an original time instant in the score and `t_new` is the new time
instant after the stretching. Applying this formula to the beat times can help
you to compute the new instant BPM while keeping the same average BPM as the
performance. This functionality is provided by ``asmd.utils.mat_stretch`` for
onsets and offsets, but not for beats yet.
