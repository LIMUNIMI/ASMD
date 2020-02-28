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

Install poetry, pyenv and python
___

#. Install ``python 3``
#. Install `poetry <https://python-poetry.org/docs/#installation>`__
#. Install `pyenv <https://github.com/pyenv/pyenv#installation>`__ and fix your
   ``.bashrc``\ (optional)
#. ``pyenv install 3.6.9`` (optional, recommended python >= 3.6.9)
#. ``poetry new myproject``
#. ``cd myproject``
#. ``pyenv local 3.6.9`` (optional, recommended python >= 3.6.9)

Install ASMD
___

#. ``git clone https://framagit.org/sapo/asmd.git``
#. ``poetry add asmd/``
#. Execute ``poetry run python -m asmd.install``; alternatively run ``poetry
   shell`` and then ``python -m asmd.install``
#. Follow the steps

Now you can start developing in the parent directory (``myproject``) and
you can use ``from asmd import audioscoredataset as asd``.

Use `poetry` to manage packages of your project.

Using pip
---------

#. Install ``python 3`` (recommended python >= 3.6.9)
#. ``cd myproject``
#. ``git clone https://framagit.org/sapo/asmd.git``
#. ``cd amsd``
#. Enter the git root directory and run ``pip install -r requirements.txt``
#. ``python setup.py build_ext --inplace``
#. Execute ``python install.py``
#. Follow the steps

Now you can start developing in the parent directory (``myproject``) and
you can use ``from asmd import audioscoredataset as asd``.

Consider using `pyenv local 3.6.9` in `myproject` and `poetry` (see above).

Using eggs (not recommended)
----------------------------

Not available at now. You can still use a one-line-command if you do not want
to have the repo directory in your source code, though:

``pip install git+https://framagit.org/sapo/asmd.git`` 

or

``poetry add git+https://framagit.org/sapo/asmd.git`` 

