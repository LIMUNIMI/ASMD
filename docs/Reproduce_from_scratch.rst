Reproduce from scratch
======================

To recreate the ground-truth in our format you have to convert the annotations
using the scirpt ``generate_ground_truth.py``.

**N.B. You should have ``wget`` installed in your system, otherwise SMD
dataset can’t be downloaded.**

You can run the script with ``python 3``. You can also skip the already
existing datasets by using the ``--blacklist`` argument. If you do this,
their ground truth will not be added to the final archive, thus,
remember to backup the previous one and to merge the archives.

Generate misaligned data
------------------------

If you want, you can generate misaligned data using the ``--misalign`` option
of ``generate_ground_truth.py``. It will run ``alignment_stats.py``, which
collects data about the datasets with real non-aligned scores and saves stats
in ``_alignment_stats.pkl`` file in the working directory. Then, it runs
``generate_ground_truth.py`` using the collected statistics:  it will
generate misaligned data by using the same deviation distribution of the
available non-aligned data. 

Note that misaligned data should be annotated as ``2`` in the ``ground_truth``
value of the dataset groups description (see :doc:`./index` ), otherwise no
misaligned value will be added to the ``misaligned`` field. Moreover, the
dataset group data should have `precise_alignment` or `broad_alignment` filled
by the annotation conversion step, otherwise errors can raise during the
misalignment procedure.

``generate_ground_truth.py`` help page
--------------------------------------
.. code:: text

    usage: generate_ground_truth.py [-h] [--misalign] [--whitelist [WHITELIST
            [WHITELIST ...]]] [--blacklist [BLACKLIST [BLACKLIST ...]]]

    Generate ASMD ground-truth from other sources

    optional arguments:
      -h, --help            show this help message and exit
      --misalign            Generate ground-truth, compute alignment stats,
                            regenerate groundtruth with artificial misalignment
      --whitelist [WHITELIST [WHITELIST ...]]
                            List of datasets that will not be excluded
                            (default: all)
      --blacklist [BLACKLIST [BLACKLIST ...]]
                            List of datasets that will be excluded (default:
                            empty). Overwrites `--whitelist`
