#cython: language_level=3
import pyximport; pyximport.install()
from conversion_tool import create_gt
from alignment_stats import Stats
import sys
print("Usage: ")
print("  python3 convert_gt.py [list of datasets to be excluded]")
print()

create_gt('datasets.json', sys.argv, gztar=True)
