from setuptools import setup

setup(
    name='nose_bisect',
    version='1.0',
    py_modules=['nose_bisect'],
    entry_points = {
        'nose.plugins.0.10': ['nose_bisect = nose_bisect:Bisector'],
    },
)
