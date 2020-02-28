from .conversion_tool import create_gt
import os
import sys
print("Usage: ")
print("  python3 generate_ground_truth.py [list of datasets to be excluded]")
print()

THISDIR = os.path.dirname(os.path.realpath(__file__))

create_gt(os.path.join(THISDIR, 'datasets.json'), sys.argv, gztar=True)
