import argparse
import os

from . import alignment_stats
from .conversion_tool import create_gt

THISDIR = os.path.dirname(os.path.realpath(__file__))

argparser = argparse.ArgumentParser(
    description='Generate ASMD ground-truth from other sources')

argparser.add_argument(
    '--misalign',
    action='store_true',
    help="Generate ground-truth, compute alignment stats, regenerate groundtruth with artificial misalignment"
)

argparser.add_argument(
    '--whitelist',
    help="List of datasets that will not be excluded (default: all)",
    nargs='*')

argparser.add_argument(
    '--blacklist',
    help="List of datasets that will be excluded (default: empty). Overwrites `--whitelist`",
    nargs='*')

args = argparser.parse_args()

create_gt(os.path.join(THISDIR, 'datasets.json'),
          gztar=True,
          alignment_stats=None,
          whitelist=args.whitelist,
          blacklist=args.blacklist)

if args.misalign:
    stats = alignment_stats.main()
    create_gt(os.path.join(THISDIR, 'datasets.json'),
              gztar=True,
              alignment_stats=stats,
              whitelist=args.whitelist,
              blacklist=args.blacklist)
