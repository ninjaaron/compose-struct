from setuptools import setup

package = 'compose_struct'
version = '0.4'
with open('README.rst') as fh:
    long_description = fh.read()

setup(name=package,
      version=version,
      description="yet another namedtuple alternative",
      long_description=long_description,
      url='https://github.com/ninjaaron/compose-struct',
      packages=['compose'],
      python_requires='>=3.5')
