# A META-DATASET FOR AUDIO-SCORE PROCESSING

This file describes multiple datasets containing data about music performances.
All the datasets are described with the same fields, so that you can use them
easily disregarding their internal structure

- [Usage](#usage)
  * [datasets.json](#datasetsjson)
  * [Ground-truth json format](#ground-truth-json-format)
  * [API](#api)
    + [Matlab [outdated]](#matlab-(outdated))
    + [Python](#python)
    + [Julia](#julia)
  * [Installation](#installation)
- [Reproduce from scratch](#reproduce-from-scratch)
- [Adding new datasets](#adding-new-datasets)
  * [Adding sections to `datasets.json`](#adding-sections-to--datasetsjson-)
  * [Provide a conversion function](#provide-a-conversion-function)
  * [Add your function to `func_map`](#add-your-function-to--func-map-)
  * [Run `generate_ground_truth.py`](#run--conversion-gt-)
  * [Generate misaligned data](#generate--misaligned--data)

# Usage

## datasets.json 

The root element is a dictionary with fields:
1. `author`: string containing the name of the author
2. `year`: int containing the year
3. `install_dir`: string containing the install directory
4. `datasets`: list of datasets object

Each dataset is an item in a global list `datasets`.  Each dataset has the
following field:

1. `ensemble`: `true` if contains multiple instruments, `false` otherwise
2. `instruments`: the list of the instruments contained in the dataset
3. `sources`:
    1. `format`: the format of the audio recordings of the single
source-separated tracks
4. `recording`:
    1. `format`: the format of the audio recordings of the mixed tracks
5. `ground_truth`: *N.B. each ground_truth has an `int` value, indicating `0` -> false, `1` -> true (manual or mechanical - Disklavier - annotation), `2` -> true (automatic annotation with state-of-art algorithms)*
    1. `non_aligned`: `true` if non_aligned scores are provided
    2. `broad_alignment`: `true` if broad_alignment scores are provided
    3. `precise_alignment`: `true` if precisely aligned scores are provided
    4. `velocities`: `true` if velocities are provided
    5. `f0`: `true` if f0 values are provided
6.  `songs`: the list of songs in the dataset
    1. `composer`: the composer family name
    2. `instruments`: list of instruments in the song
    3. `recording`: dictionary
        1. `path`: a list of paths to be mixed for reconstructing the full track
(usually only one)
    4. `sources`: dictionary
        1. `path`: a list of paths to the single instrument tracks in the same
order as `instruments`
    5. `ground_truth`: list of paths to the ground_truth json files.
One ground_truth path per instrument is alway provided. The order of the 
ground_truth path is the same of sources and of the instruments. Note that 
some ground_truth paths can be identical (as in PHENICX for indicating that 
violin1 and violin2 are playing exactly the same thing).
7.  `url`: the url to download the dataset including the protocol
8.  `post-process`: a list of shell commands to be executed to prepare the
dataset; they can be lists themselves to allow the use of anchors to
install_dir" field with the syntax "&install_dir"
9.  `unpack`: `true` if the url needs to be unpacked


In general, I maintained the following principles:
1. if a list of files is provided where you would logically expect one file, you
should 'sum' the files in the list, whatever this means according to that
type of file; this typically happens in the `ground_truth` files. or in the
recording where only the single sources are available.
2. all the fields can have the value 'unknown' to indicate that it is not
available in that dataset; if you treat 'unknown' with the meaning of
unavailable everything will be fine; however, in some cases it can mean that
the data are available but that information is not documented.

## Ground-truth json format

The ground_truth is contained in json files indexed in `datasets.json`. Each
ground truth file contains only one isntrument in a dictionary with the
following structure:
1. `non_aligned`:
    1. `onsets`: onsets in seconds at 20 bpm
    2. `offsets`: offsets in seconds at 20 bpm
    3. `pitches`: list of midi pitches in onset ascending order
    4. `note`: list of note names in onsets ascending order
    5. `velocities`: list of velocities in onsets ascending order
2. `precise_alignment`:
    1. `onsets`: onsets in ms
    2. `offsets`: offsets in ms
    3. `pitches`: list of midi pitches in onset ascending order
    4. `note`: list of note names in onsets ascending order
    5. `velocities`: list of velocities in onsets ascending order
3. `broad_alignment`: alignment which does not consider the asynchronies between
simultaneous notes
    1. `onsets`: onsets in ms
    2. `offsets`: offsets in ms
    3. `pitches`: list of midi pitches in onset ascending order
    4. `note`: list of note names in onsets ascending order
    5. `velocities`: list of velocities in onsets ascending order
4. `f0`: list of f0 frequencies, frame by frame (frame rate according to the
source sound file or to the whole recording sound file if sources are not
available)
6. `instrument`: General Midi program number associated with this instrument,
starting from 0. 128 indicates a drum kit (should be synthesized on channel 8
with a program number of your choice, usually 0).

Note that json ground_truth files have extension `.json.gz`, indicating that
they are compressed using the `gzip` Python 3.7 module. Thus, you need to
decompress them:
```python import lzma import json

ground_truth = json.load(gzip.open('ground_truth.json.gz', 'rt'))

print(ground_truth)

```

## API

This project also provides a few API for filtering the datasets according
to some specified prerequisites and getting the data in a convenient format.

### Matlab [outdated]

Add this directory to your path and create an `AudioScoreDataset` object, giving
the path of the `datasets.json` file in this directory as argument to the
constructor. Then, you can use the `filter_data` method to filter data according
to your needs (you can also re-filter them later without reloading
`datasets.json`). After this, you can move the ground truth files (compressed)
to RAM by using a `tmpfs` file system (if you do not have enough RAM, you can
use `tmpfs` to just decompress the ground truth files one-by-one).

You will find a value `paths` in your `AudioScoreDataset` instance containing
the correct paths to the files you are requesting.

Moreover, the method `get_item` returns an array of audio values and a
structured_array representing the ground_truth as loaded from the json file.

Example:

```matlab
d = AudioScoreDataset('datasets.json');
d.filter('instrument', 'piano', 'ensemble', false, 'composer', 'Mozart', 'ground_truth', 'precise_alignment');
d.move_to_ram('/mnt/tmpfs'); % discouraged but maybe can turn to be useful
d.set_decompress_path('/mnt/tmpfs'); % only if you don't have enough space in RAM, discouraged

audio_array, sources_array, ground_truth_array = d.get_item(1);

audio_array = d.get_mix(2);
source_array = d.get_source(2);
ground_truth_array = d.get_gts(2);

disp(d.paths);
```

### Python
Import `audioscoredataset` and create a `Dataset` object, giving
the path of the `datasets.json` file in this directory as argument to the
constructor. Then, you can use the `filter` method to filter data according
to your needs (you can also re-filter them later without reloading
`datasets.json`).

You will find a value `paths` in your `Dataset` instance containing
the correct paths to the files you are requesting.

Moreover, the method `get_item` returns an array of audio values and a
structured_array representing the ground_truth as loaded from the json file.

Example:

```python
import audioscoredataset as asd
d = asd.Dataset('./datasets.json')
d.filter(instrument='piano', ensemble=False, composer='Mozart', ground_truth=['precise_alignment'])

audio_array, sources_array, ground_truth_array = d.get_item(1)

audio_array = d.get_mix(2)
source_array = d.get_source(2)
ground_truth_list = d.get_gts(2)

mat = d.get_score(2, score_type=['precise_alignment'])

```

Note that you can inherit from `audioscoredataset.Dataset` and `torch.utils.data.Dataset` to create a PyTorch
compatible dataset which only load audio files when thay are accessed. You will just need to implement the
`__getitem__` method.

### Julia 
[TODO]

## Installation
1. Install `python 3`
2. Run the following command from a shell terminal from inside this directory:
python3 install.py
3. Follow the steps.

# Reproduce from scratch

If you want, you can also recreate the annotations
from scratch by running the python 3 script `convert_gt.py` after having
installed the datasets.

**N.B. You should have `wget` installed in your system, otherwise SMD dataset
can't be downloaded.**

# Adding new datasets
In order to add new datasets, you have to:

1. Add the correspondent section in `datasets.json`
2. Provide a conversion function for the ground truth
3. Add the conversion function to the structure `func_map` in `convert_from_file.py`
4. Rerun the `convert_gt.py` script

## Adding sections to `datasets.json`

The most important thing is that one ground-truth file is provided for each
instrument. Add the paths, even if they still do not exist, because
`convert_gt.py` relies on that to create them. It is important to provide an
index starting with `-` at the end of the path (see the other sections as
example), so that it is possible to distinguish among multiple instruments (for
instance, PHENICX provides one ground-truth file for all the violins of a song,
even if there are 4 different violins). The index allows `convert_gt` to better
handle different files and to pick the ground-truth wanted.

It is mandatory to provide a url, a name and so on. Also, provide a composer
and instrument list. Please, do not use new words for instruments already
existing (for instance, do not use `saxophone` if `sax` already exists in other
datasets).

After this, you should install the dataset by running the installation script.

## Provide a conversion function in `convert_from_file.pyx`

The conversion function takes as input the name of the file to be created (i.e.
the paths added to the new `datasets.json` section) and outputs a list of
dictionaries. You should:

1. use `change_ext` to recreate the input file name (this also takes care of the
final index removal)
2. use `deepcopy(gt)` to create the output ground truth.

In future, these to operations should be automated with a more object-oriented
approach.  You should consider three possible cases for creating the conversion function:

1. there is a bijective relationship between instruments and ground_truth file
you have, that is, you already have a convesion file per each instrument and
you should just convert all of them ( _1-to-1 relationship_ )
2. in your dataset, all the instruments are inside just one ground-truth file (
_n-to-1 relationship_ )
3. just one ground-truth file is provided that replicates for multiple
instruments (one ground-truth for all the `violins`, as if they were a
single instrument, _1-to-n relationship_ )

Here is a brief description of how your conversion function should work to
tackle these three different situations.
- In the 1st case, you can just output a list with only one dictionary.
- In the 2nd case, you can output a list with all the dictionary inside it, in
    the same order as the ground-truth file paths you added to `datasets.json`. The
    script will repeatly convert them and each times it will pick a different
    element of the list.
-  In the 3rd case, you can still output a single element list.

Finally, you can also use multiple conversion functions if your ground-truth is
splitted among multiple files, but note that the final ground-truth is produced
as the sum of all the elements of all the dictionaries created.

**The core of the conversion is the function `conversion_tool.merge`. Read it
and be sure to understand its behavior.** Please, take care of how the `merge`
function behaves with your conversion function, since it is really hard to
write a single `merge` function for all the possible representations. It should
work, but please, take care of it.

## Add your function to `func_map`

In `convert_from_file.py` you can find a dictionary called `func_map`. It is a
dictionary which stores all the functions that are needed and their parameters
for each dataset. The keys are the datasets name you added in `datasets.json`.
The element is a list of tuples like this: 

```python
    [
        (
            function1, {
                'argument1_name': argument1_value,
                'argument2_name': argument2_value
            }
        ), 
        (
            function2, {
                'argument1_name': argument1_value, 
                'argument2_name': argument2_value
            }
        )
    ]
```

## Run `generate_ground_truth.py`

You can run the script with `python 3`. You can also skip the already existing
datasets by simply add their names as argument. If you do this, their ground
truth will not be added to the final archive, thus, remember to backup the
previous one and to merge the archives.

## Generate misaligned data

If you want, you can generate misaligned data. First, after having created the
ground-truth, run `alignment_stats`, which collects data about the datasets
with real non-aligned scores and saves stats in a pickled file in this
directory. Then, run `generate_ground_truth.py` again: it will load the pickled file and
will generate misaligned data by using the same deviation distribution of the
available non-aligned data.

Note that misaligned data should be annotated as `2` in the `ground_truth` value
of the dataset description (see [datasets.json](#datasetsjson) ), otherwise no
misaligned value will be added to the `non_aligned` field.
