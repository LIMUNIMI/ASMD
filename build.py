from distutils.extension import Extension
from Cython.Build import cythonize

extensions = [
    Extension("asmd.audioscoredataset", ["asmd/audioscoredataset.pyx"]),
    Extension("asmd.convert_from_file", ["asmd/convert_from_file.pyx"]),
    Extension("asmd.conversion_tool", ["asmd/conversion_tool.pyx"]),
    Extension("asmd.utils", ["asmd/utils.pyx"])
]


def build(setup_kwargs):
    setup_kwargs.update({
       'ext_modules': cythonize(
            extensions,
            compiler_directives={
                'language_level': "3",
                'embedsignature': True
            })
       })
