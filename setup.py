from setuptools import setup, find_packages
import os
import glob

def find_data_files(source, target, patterns):
    if glob.has_magic(source) or glob.has_magic(target):
        raise ValueError("Magic not allowed in src, target")
    ret = {}
    for pattern in patterns:
        pattern = os.path.join(source, pattern)
        for filename in glob.glob(pattern):
            if os.path.isfile(filename):
                targetpath = os.path.join(target, os.path.relpath(filename, source))
                path = os.path.dirname(targetpath)
                ret.setdefault(path, []).append(filename)
    return sorted(ret.items())

setup(
    name='FunduckESS',
    version='1.1',
    author='Damir Akhmetzyanov',
    description='Expert System Shell',
    packages=find_packages(),
    install_requires=['PyQt5>=5.15.0'],
    entry_points={
        'console_scripts': ['funduck_ess=Shell:main'],
    },
    data_files=find_data_files('', '', [
        'LICENSE.txt',
        'COPYING',
        'icons/*',
        'demo/*.es'
    ]),
    zip_safe=False
)