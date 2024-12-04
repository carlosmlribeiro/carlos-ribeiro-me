from setuptools import setup, find_packages

setup(
    name="app",
    packages=find_packages(include=['app', 'app.*']),
    version="0.1.0",
) 