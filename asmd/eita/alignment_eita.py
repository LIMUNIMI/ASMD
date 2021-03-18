import csv
import os
import random
import sys
from pathlib import Path
from subprocess import Popen, TimeoutExpired
from typing import Union

import numpy as np

from .. import utils
from ..idiot import THISDIR

# import time

# from . import align
# from . import settings as s
EITA_PATH = Path(THISDIR) / 'eita'


def which(program: Union[str, Path]):
    """
    Stolen from stackoverflow
    """
    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


def check_executables():
    """
    1. check if program compiled exists
    2. if not, suggests the command line to compile it

    Returns True if exists, False otherwise
    """

    for ex in [
            'midi2pianoroll', 'SprToFmt3x', 'Fmt3xToHmm', 'ScorePerfmMatcher',
            'ErrorDetection', 'RealignmentMOHMM', 'MetchToCorresp'
    ]:
        if not which(EITA_PATH / 'Programs' / ex):
            print(
                "Eita tools seems to be uncorrectly compiled, please use the following command to compile",
                file=sys.stderr)
            print(f"`{EITA_PATH}/compile.sh`")


def remove_temp_files(path: Union[str, Path]):
    path = Path(path)
    for file in path.parent.glob(path.stem + "*"):
        file.unlink()


# def eita_align(
#         matscore: np.ndarray,
#         matperfm: np.ndarray) -> Optional[Tuple[np.ndarray, np.ndarray]]:
#     """
#     0. runs the alignment
#     2. clean the output files
#     3. returns new onsets and offsets or None if something fails
#     """
#     ttt = time.time()
#     matched_idx = get_matching_notes(matscore, matperfm)
#     if matched_idx is None:
#         return None

#     print(f"Exectued in {time.time() - ttt: .2f} seconds")
#     print(f"Number of matching notes: {matched_idx.shape[0]}")

#     align.align_with_matching_notes(matched_idx, matscore, matperfm)

#     return matscore[:, 1], matscore[:, 2]


def get_matching_notes(matscore: np.ndarray, matperfm: np.ndarray):
    """
    Returns a mapping of indices between notes in `matscore` and in `matperfm`
    with shape (N, 2), where N is the number of matching notes.

    Performs Eita Nakamura alignment in a separate process and waits for it.
    This cleans all the output files. Returns None if the separate process
    fails.
   ta """

    p1 = random.randint(10**6, 10**7)
    p2 = p1 + 1
    path1 = str(p1) + '.mid'
    path2 = str(p2) + '.mid'

    # writing music data to midi files
    # the first argument is the reference signal
    utils.mat2midipath(matperfm, path1)
    utils.mat2midipath(matscore, path2)

    # Launch the external process
    popen = Popen([f"{EITA_PATH}/MIDIToMIDIAlign.sh", path1[:-4], path2[:-4]])
    try:
        popen.wait(timeout=10)
    except TimeoutExpired:
        print("Alignment failed!")
        return None
    if popen.returncode != 0:
        return None

    # load the output
    eita_data = []
    with open(path2[:-4] + "_corresp.txt", newline='') as f:
        csv_reader = csv.reader(f, delimiter='\t')
        next(csv_reader)  # skip first row (the file is not a real csv file...)
        for row in csv_reader:
            if row[1] != '-1' and row[6] != '-1':
                eita_data.append((int(row[0]), int(row[5])))

    # remove files created by eita code
    remove_temp_files(path1)
    remove_temp_files(path2)

    # removing rows with -1 (not matched notes)
    return np.array(eita_data, dtype=np.int)
