Reproduce from scratch
======================

To recreate the ground-truth in our format you have to convert the annotations.

#. run ``generate_ground_truth.py`` script after having installed the datasets
   with the ``install.py`` (see :doc:`Installation`)
#. to recreate artificial misalignment estimation, then you should also

   #. run ``alignment_stats.py`` 
   #. ``generate_ground_truth.py`` again.

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

If you want, you can generate misaligned data. First, after having
created the ground-truth, run ``alignment_stats.py``, which collects data
about the datasets with real non-aligned scores and saves stats in
``_alignment_stats.pkl`` file in the working directory. Then, run
``generate_ground_truth.py`` again: it will load the pickled file and
will generate misaligned data by using the same deviation distribution
of the available non-aligned data. If you don't delete the
``_alignment_stats.pkl`` file, every time you run ``generate_ground_truth.py``
it will create artificial misalignments.

Note that misaligned data should be annotated as ``2`` in the
``ground_truth`` value of the dataset description (see
:doc:`./index` ), otherwise no misaligned value will
be added to the ``non_aligned`` field.
