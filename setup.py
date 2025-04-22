import setuptools
import distutils.core

setuptools.setup(
    name='gh-star-timeline',
    version="1.1.0",
    author='@readwithai',
    long_description_content_type='text/markdown',
    author_email='talwrii@gmail.co',
    description='Command-line tool to keep track of historic stars on github. Machine-useable output.',
    license='GPLv3',
    keywords='',
    url='',
    packages=["gh_star_timeline"],
    long_description=open('README.md').read(),
    entry_points={
        'console_scripts': ['gh-star-timeline=gh_star_timeline.main:main']
    },
    classifiers=[
    ],
    test_suite='nose.collector'
)
