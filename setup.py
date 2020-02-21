from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize

extensions = [
    Extension("audioscoredataset", ["audioscoredataset.pyx"]),
    Extension("convert_from_file", ["convert_from_file.pyx"]),
    Extension("conversion_tool", ["conversion_tool.pyx"])
]

setup(
    ext_modules=cythonize(
        extensions,
        compiler_directives={
            'language_level': "3",
            'embedsignature': True
        }
    )
)
