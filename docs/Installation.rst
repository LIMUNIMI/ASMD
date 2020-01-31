Installation
============

I suggest to clone this repo and to use it with python >= 3.6. If you
need to use it in multiple projects (or folders), just clone the code and
fix the ``install_dir`` in ``datasets.json``, so that you can have only
one copy of the huge datasets.

The following describes how to install dependecies needed for the usage of the
dataset API. I suggest to use  `poetry <https://python-poetry.org/>`__ to manage
different versions of python and virtual environments with an efficient
dependency resolver.

During the installation, the provided ground-truth will be extracted; however,
you can recreate them from scratch for tweaking parameters. The next section
will explain how you can achieve this.

Using Poetry (recommended)
--------------------------

Once you have cloned the repo follow these steps:

#. Install ``python 3``
#. Install `poetry <https://python-poetry.org/docs/#installation>`__
#. Install `pyenv <https://github.com/pyenv/pyenv#installation>`__ and fix your ``.bashrc``\ (optional)
#. ``pyenv install 3.6.9`` (optional, recommended python >= 3.6.9)
#. ``cd myproject``
#.  ``touch __init__.py``
#. ``pyenv local 3.6.9`` (optional)
#.  ``git clone https://framagit.org/sapo/asmd.git``
#. ``cd amsd``
#. ``poetry install``
#. Execute ``poetry run python install.py``
#. Follow the steps

Now you can start developing in the parent directory (``myproject``) and
you can use ``from asmd import audioscoredataset as asd``.

Using pip
---------

#. Install ``python 3`` (recommended python >= 3.6.9)
#. ``cd myproject``
#. ``git clone https://framagit.org/sapo/asmd.git``
#. ``cd amsd``
#. Enter the git root directory and run ``pip install -r requirements.txt``
#. Execute ``poetry run python install.py``
#. Follow the steps

Now you can start developing in the parent directory (``myproject``) and
you can use ``from amsd import audioscoredataset as asd``.

Using pypi (not recommended)
----------------------------

Not available at now.
