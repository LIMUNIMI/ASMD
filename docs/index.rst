ASMD: Audio-Score Meta Dataset
================================

.. toctree::
   :maxdepth: 2
   :caption: Table of Contents
   
   Installation
   Reproduce_from_scratch
   JSON
   Adding_datasets
   Converting
   API
   Utilities
   Scientific_notes
   License
   Source Code and Download <https://framagit.org/sapo/asmd>

This paper describes an open-source Python framework for handling datasets for
music processing tasks, built with the aim of improving the reproducibility of
research projects in music computing and assessing the generalization abilities
of machine learning models. The framework enables the automatic download and
installation of several commonly used datasets for multimodal music processing.
Specifically, we provide a Python API to access the datasets through Boolean
set operations based on particular attributes, such as intersections and unions
of composers, instruments, and so on. The framework is designed to ease the
inclusion of new datasets and the respective ground-truth annotations so that
one can build, convert, and extend one's own collection as well as distribute
it by means of a compliant format to take advantage of the API. All code and
ground-truth are released under suitable open licenses.

For a gentle introduction, see our paper [1]
   

TODO
====

#. move wget to curl
#. support Windows systems


Cite us
=======

[1]  Simonetta, Federico ; Ntalampiras, Stavros ; Avanzini, Federico: *ASMD: an automatic framework for compiling multimodal datasets*. In: Proceedings of the 17th Sound and Music Computing Conference. Torino, 2020 arXiv:2003.01958_

.. _arXiv:2003.01958: https://arxiv.org/abs/2003.01958

---

Federico Simonetta

* https://lim.di.unimi.it
* https://federicosimonetta.eu.org

Indices
=======

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
