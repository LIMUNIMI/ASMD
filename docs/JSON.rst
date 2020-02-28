Usage
=====

datasets.json
-------------

The root element is a dictionary with fields:

#. ``author``: string containing the name of the author
#. ``year``: int containing the year
#. ``install_dir``: string containing the install directory
#. ``datasets``: list of datasets object
#. ``decompress_path``: the path were files are decompressed

Definitions
-----------

Each dataset is described by a JSON file which. Each dataset has the
following field:

#. ``ensemble``: ``true`` if contains multiple instruments, ``false`` otherwise
#. ``instruments``: the list of the instruments contained in the dataset
#. ``sources``:

   #. ``format``: the format of the audio recordings of the single source-separated tracks

#. ``recording``:

   #. ``format``: the format of the audio recordings of the mixed tracks

#. ``ground_truth``: *N.B. each ground_truth has an ``int`` value, indicating ``0`` -> false, ``1`` -> true (manual or mechanical - Disklavier - annotation), ``2`` -> true (automatic annotation with state-of-art algorithms)*

   #. ``non_aligned``: ``true`` if non_aligned scores are provided
   #. ``broad_alignment``: ``true`` if broad_alignment scores are provided
   #. ``precise_alignment``: ``true`` if precisely aligned scores are provided
   #. ``velocities``: ``true`` if velocities are provided
   #. ``f0``: ``true`` if f0 values are provided

#. ``songs``: the list of songs in the dataset

   #. ``composer``: the composer family name
   #. ``instruments``: list of instruments in the song
   #. ``recording``: dictionary
   
      #. ``path``: a list of paths to be mixed for reconstructing the full track (usually only one)
      
   #. ``sources``: dictionary
   
      #. ``path``: a list of paths to the single instrument tracks in the same order as ``instruments``
      
   #. ``ground_truth``: list of paths to the ground_truth json files.  One ground_truth path per instrument is always provided. The order of the ground_truth path is the same of sources and of the instruments. Note that some ground_truth paths can be identical (as in PHENICX for indicating that violin1 and violin2 are playing exactly the same thing).
   
#. ``install``: where information for the installation process are stored

   #. ``url``: the url to download the dataset including the protocol
   #. ``post-process``: a list of shell commands to be executed to prepare the   dataset; they can be lists themselves to allow the use of anchors to install_dir" field with the syntax “&install_dir”
   #. ``unpack``: ``true`` if the url needs to be unpacked
   #. ``login``: true if you a login is needed - no more used, but maybe useful in future

In general, I maintained the following principles:

#. if a list of files is provided where you would logically expect one file, you should ‘sum’ the files in the list, whatever this means according to that type of file; this typically happens in the ``ground_truth`` files. or in the recording where only the single sources are available.
#. all the fields can have the value ‘unknown’ to indicate that it is not available in that dataset; if you treat ‘unknown’ with the meaning of unavailable everything will be fine; however, in some cases it can mean that the data are available but that information is not documented.

Ground-truth json format
------------------------

The ground_truth is contained in JSON files indexed in each definition
file. Each ground truth file contains only one isntrument in a
dictionary with the following structure:

#. ``non_aligned``:

   #. ``onsets``: onsets in seconds at 20 bpm
   #. ``offsets``: offsets in seconds at 20 bpm
   #. ``pitches``: list of midi pitches in onset ascending order
   #. ``note``: list of note names in onsets ascending order
   #. ``velocities``: list of velocities in onsets ascending order

#. ``precise_alignment``:

   #. ``onsets``: onsets in ms
   #. ``offsets``: offsets in ms
   #. ``pitches``: list of midi pitches in onset ascending order
   #. ``note``: list of note names in onsets ascending order
   #. ``velocities``: list of velocities in onsets ascending order

#. ``broad_alignment``: alignment which does not consider the asynchronies between simultaneous notes

   #. ``onsets``: onsets in ms
   #. ``offsets``: offsets in ms
   #. ``pitches``: list of midi pitches in onset ascending order
   #. ``note``: list of note names in onsets ascending order
   #. ``velocities``: list of velocities in onsets ascending order

#. ``f0``: list of f0 frequencies, frame by frame (frame rate according to the source sound file or to the whole recording sound file if sources are not  available)
#. ``instrument``: General Midi program number associated with this instrument, starting from 0. 128 indicates a drum kit (should be synthesized on channel 8 with a program number of your choice, usually 0).

Note that json ground_truth files have extension ``.json.gz``,
indicating that they are compressed using the ``gzip`` Python 3.7
module. Thus, you need to decompress them:

.. code: python

    import gzip
    import json

    ground_truth = json.load(gzip.open(‘ground_truth.json.gz’, ‘rt’))

    print(ground_truth)

