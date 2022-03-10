from setuptools import setup, find_packages

__version__ = '0.0.1'


setup(name='python-seafile-2022',
      version=__version__,
      license='BSD',
      description='Client interface for Seafile Web API(2022)',
      author='Igor Rumyantsev, Andrey Skhomenko',
      author_email='andrew.foma@gmail.com',
      url='https://github.com/JohnEskimSmith/python-seafile-2022',
      platforms=['Any'],
      packages=find_packages(),
      install_requires=['requests'],
      classifiers=['Development Status :: 4 - Beta',
                   'License :: OSI Approved :: BSD License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python'],
      )
