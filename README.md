# A META-DATASET FOR AUDIO-SCORE PROCESSING

This file describes multiple datasets containing data about music
performances. All the datasets are described with the same fields, so that
you can use them easily disregarding their internal structure


## datasets.json
The root element is a dictionary with fields:
1. `author`: string containing the name of the author
2. `year`: int containing the year
3. `install_dir`: string containing the install directory
4. `datasets`: list of datasets object

Each dataset is an item in a global list `datasets`.
Each dataset has the following field:
1. `ensemble`: `true` if contains multiple instruments, `false` otherwise
2. `instruments`: the list of the instruments contained in the dataset
3. `sources`:
    1. `format`: the format of the audio recordings of the single
source-separated tracks
4. `recording`:
    1. `format`: the format of the audio recordings of the mixed tracks
5. `ground-truth`:
    1. `format`: the format of the ground-truth files
    2. `non-aligned`: `true` if non-aligned scores are provided
    3. `errors`: a list with the type of errors provided, or 'unknown'
    4. `precise-alignment`: `true` if precisely aligned scores are provided
    5. `velocities`: `true` if velocities are provided
techniques) are provided
6.  `songs`: the list of songs in the dataset unknown
    1. `composer`: the composer family name
    2. `instruments`: list of instruments in the song
    3. `recording`: dictionary
        1. `path`: a list of paths to be mixed for reconstructing the full track
    4. `sources`: dictionary
        1. `path`: a list of paths to the single instrument tracks in the same
order as `instruments`
    5. `ground-truth`: list of paths to the ground-truth json files. Ground-truth are in
bijective relationships with the single-sources (multiple paths are provided, one per
source file), or just one ground truth path is provided if no sources are available.
7.  `url`: the url to download the dataset including the protocol
8.  `post-process`: a list of shell commands to be executed to prepare the
dataset; they can be lists themselves to allow the use of anchors to "install_dir"
field with the syntax "&install_dir"
9.  `unpack`: `true` if the url needs to be unpacked


In general, I maintained the following principles:
1. if a list of files is provided where you would logically expect one file,
you should 'sum' the files in the list, whatever this means according to that
type of file; this typically happens in the `ground-truth` files. or in the recording
where only the single sources are available.
2. all the fields can have the value 'unknown' to indicate that it is not
available in that dataset; if you treat 'unknown' with the meaning of unavailable everything will be fine; however, in some cases it can mean that the data are available but that information is not documented.

## Ground-truth json format

The ground-truth is contained in json files indexed in `datasets.json`. Each ground truth
file contains a dictionary with the following structure:
1. `non-aligned`:
    1. `onsets`: onsets in quarter notation
    2. `offsets`: offsets in quarter notation
2. `precise-alignment`:
    1. `onsets`: onsets in ms
    2. `offsets`: offsets in ms
3. `broad_alignment`: alignment which does not consider the asynchronies between
simultaneous notes
    1. `onsets`: onsets in ms
    2. `offsets`: offsets in ms
4. `pitches`: list of midi pitches in onset ascending order
5. `f0`: list of f0 frequencies, frame by frame (frame rate according to the source sound
file or to the whole recording sound file if sources are not available)
6. `note`: list of note names in onsets ascending order
7. `velocities`: list of velocities in onsets ascending order

Note that json ground-truth files have extension `.json.xz`, indicating that they are
compressed using the `lzma` Python 3.7 module. Thus, you need to decompress them:

```python
import lzma
import json

ground_truth = json.load(lzma.open('ground-truth.json.xz', 'rt'))

print(ground_truth)
```

## API
This project also provides a few API for filtering the datasets according to some
specified prerequisites and getting the data in a convenient format.

### Matlab

Add this directory to your path and use the function `load_data`.

### Python

Add this directory to your path, add `from audiodatasets import load_data` and use the
function `load_data`.

## Installation
1. Install `python 3`
2. Run the following command from a shell terminal from inside this
directory: python3 install.py
3. Follow the steps.

## Reproduce from scratch
If you want, you can also recreate the annotations from scratch by running the python 3
script `convert_gt.py` after having installed the datasets.

**N.B. You should have `wget` installed in your system, otherwise SMD dataset
can't be downloaded.**

