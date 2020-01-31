Scientific notes
================

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
to 0.2 (see ``conversion_tool.pyx`` lines ``17-21``).

One more problem is due to the fact that the unity of measure for time
in aligned data are seconds, while in scores are note lenghts. Ususally,
one can translates a note length to seconds by using BPM. During the
statistical analysis, I always consider the prescripted tempo as 20 BPM
(see ``convert_from_file.pyx``, line ``11``). This is not the best
option, but since I do not have the BPM of all the available scorse, I
found more convenient having all of them scored with a non-usual BPM, in
the attempt of making the BPM the least influent as possible.

