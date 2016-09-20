#!/usr/bin/env python
#

import setuptools

import readings


def read_requirements(name):
    requirements = []
    with open(name) as req_file:
        for line in req_file:
            if '#' in line:
                line = line[line.index('#')]
            line = line.strip()
            if line.startswith('-r'):
                requirements.extend(read_requirements(line[2:].strip()))
            elif line and not line.startswith('-'):
                requirements.append(line)
    return requirements


setuptools.setup(
    name='readings',
    version=readings.version,
    description='Read article tracker',
    long_description='\n'+open('README.rst').read(),
    author='Dave Shawley',
    author_email='daveshawley@gmail.com',
    url='https://github.com/dave-shawley/readings',
    license='BSD',
    packages=['readings'],
    install_requires=read_requirements('requirements.txt'),
    entry_points={'console_scripts': ['readings=readings.app:main']},
    classifiers=['Development Status :: 5 - Production/Stable',
                 'Environment :: Web Environment',
                 'Intended Audience :: Developers',
                 'License :: OSI Approved :: BSD License',
                 'Operating System :: OS Independent',
                 'Programming Language :: Python'],
)
