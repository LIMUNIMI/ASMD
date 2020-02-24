from distutils.core import setup
from build import build
from utils.build import build as utils_build

global setup_kwargs

setup_kwargs = {}

utils_build(setup_kwargs)
setup(**setup_kwargs)

build(setup_kwargs)
setup(**setup_kwargs)
