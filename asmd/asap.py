"""
This is a simple script to import scores from ASAP
"""

import argparse
import csv
import json
import tempfile
import zipfile
from pathlib import Path
from typing import List, Mapping, Set, Tuple

import requests

from .asmd import Dataset
from .dataset_utils import filter
from .idiot import THISDIR

ASAP_URL = "https://github.com/fosfrancesco/asap-dataset/archive/v1.1.zip"


def modify_maestro_definifion(index: List[Tuple[Path, Path]]) -> Mapping:
    """
    This function was run only once to add the proper group `asap` on the
    `Maestro` dataset
    """
    # create a daset for loading the Maestro definition
    for definition in Dataset().datasets:
        if definition['name'] == 'Maestro':
            break

    # convert index to Set of string for faster search (the `in` operation)
    _index: Set[str] = {str(e[0]) for e in index}

    # add `asap` to each song with ground_truth in the index
    for song in definition['songs']:
        if song['ground_truth'][0] in _index:
            song.groups.append("asap")
    return definition


def download_asap() -> tempfile.TemporaryDirectory:
    """
    Download ASAP from github. return the Path to the downloaded dir
    """
    # downloading
    print("Downloading ASAP")
    res = requests.get(ASAP_URL)

    asap_dir = tempfile.TemporaryDirectory()
    with tempfile.TemporaryFile() as f:
        f.write(res.content)
        print("Uncompressing ASAP")
        with zipfile.ZipFile(f, 'r') as zip_ref:
            zip_ref.extractall(str(asap_dir))

    return asap_dir


def make_index(asap_path: Path) -> List[Tuple[Path, Path]]:
    """
    Generate a list of tuples with values:
        Maestro midi paths, ASAP midi score path
    """
    # a random path inside asmd
    dataset = Dataset()
    asmd_maestro_random_path = filter(dataset,
                                      datasets=['Maestro']).get_gts_paths(0)[0]
    # the second occurrence of `/` in the random path
    _idx = asmd_maestro_random_path.index('/',
                                          asmd_maestro_random_path.index('/'))

    # construct path to asmd Maestro
    asmd_maestro = Path(dataset.install_dir) / asmd_maestro_random_path[:_idx]

    out: List[Tuple[Path, Path]] = []
    with open(asap_path / 'metadata.csv') as f:
        for row in csv.DictReader(f):
            maestro_path = row['maestro_midi_performance']
            if maestro_path:
                out.append(
                    (Path(maestro_path.replace('{maestro}', asmd_maestro)),
                     asap_path / row['midi_score']))

    return out


def copy_scores(index: List[Tuple[Path, Path]]):
    """
    Moves the scores in `index` to the Maestro path using `.score.mid`
    extension
    """

    # moving files
    for maestro, asap in index:
        asap.rename(maestro.with_suffix('.score.mid'))


if __name__ == '__main__':
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-m", "--modify", action='store_true')
    args = argparser.parse_args()

    with download_asap() as asap_dir:
        index = make_index(Path(str(asap_dir)))
        if args.modify:
            new_def = modify_maestro_definifion(index)
            json.dump(new_def,
                      open(Path(THISDIR) / 'definitions' / 'Maestro.json'))
        else:
            copy_scores(index)
