Reproduce from scratch
======================

To recreate the ground-truth in our format you have to convert the annotations.
Then, you have two modalities to use ASMD:

#. using alignment from the original sources: run ``generate_ground_truth.py``
   script after having installed the datasets with the ``install.py`` (see
   :doc:`Installation`)
#. using alignment with artificial misalignment estimation: run
   ``generate_ground_truth.py --misalign``

The second modality is usually preferred because it assures that the number of
notes in the scores and in the audio are exactly the same. Moreover, it
provides alignment for datasets that do not have it.

To only create statistics, and plot histograms, run ``alignment_stats.py`` 

**N.B. You should have ``wget`` installed in your system, otherwise SMD
dataset can’t be downloaded.**

The following explain what these scripts are doing.

Run ``generate_ground_truth.py``
--------------------------------

You can run the script with ``python 3``. You can also skip the already
existing datasets by simply add their names as argument. If you do this,
their ground truth will not be added to the final archive, thus,
remember to backup the previous one and to merge the archives.

Generate misaligned data
------------------------

If you want, you can generate misaligned data using the ``--misalign`` option
of ``generate_ground_truth.py``. It will first run the usual
``generate_ground_truth.py`` without options, then it will run
``alignment_stats.py``, which collects data about the datasets with real
non-aligned scores and saves stats in ``_alignment_stats.pkl`` file in the
working directory. Then, it runs ``generate_ground_truth.py`` again using the
collected statistics:  it will generate misaligned data by using the same
deviation distribution of the available non-aligned data. 

Note that misaligned data should be annotated as ``2`` in the ``ground_truth``
value of the dataset description (see :doc:`./index` ), otherwise no misaligned
value will be added to the ``non_aligned`` field.
