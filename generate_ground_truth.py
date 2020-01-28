#cython: language_level=3
import pyximport; pyximport.install()
from conversion_tool import create_gt
from alignment_stats import Stats
import os
import sys
print("Usage: ")
print("  python3 convert_gt.py [list of datasets to be excluded]")
print()

THISDIR = os.path.dirname(os.path.realpath(__file__))

create_gt(os.path.join(THISDIR, 'datasets.json'), sys.argv, gztar=True)
