from distutils.core import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize(
        "conversion_tool.pyx",
        "convert_from_file.pyx",
        "audioscoredataset.pyx",
        compiler_directives={
            'language_level': "3",
            'embedsignature': True
        }
    )
)
