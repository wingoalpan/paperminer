#!C:\Users\pypy2\AppData\Local\Programs\Python\Python311\python.exe

from __future__ import print_function
from setuptools import setup, find_packages

setup(
    name="paperminer",
    version="0.1.0",
    author="Wingoal",  # 作者名字
    author_email="panwingoal@gmail.com",
    description="Paper lineage miner and a paper viewer.",
    license="MIT",
    url="https://github.com/wingoalpan/paperminer",  # github地址或其他地址
    packages=['paperminer', 'test', 'paperminer.web', 'paperminer.web.pages'],
    package_dir={'paperminer': 'paperminer', 'test': 'test',
                 'paperminer.web': 'paperminer/web',
                 'paperminer.web.pages': 'paperminer/web/pages'},
    package_data={'': ['*.json', 'template/*.xlsx',
                       'db/*.sql', 'db/*.db',
                       'web/assets/*.css', 'web/assets/*.js']
                  },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'paperminer=paperminer.web.webapp:start',
            'dbsql=paperminer.dbsql:main',
        ]
    },

    classifiers=[
        "Environment :: Windows Environment",
        'Intended Audience :: Academic Researchers or Technical Experts',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: Chinese',
        'Operating System :: Microsoft',
        'Operating System :: POSIX',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 3.11',
    ],
    install_requires=[
            'dash>=2.18.2',
            'dash_bootstrap_components>=1.6.0',
            'waitress>=3.0.2',
            'pandas>=2.2.3',
            'openpyxl>=3.1.5',
            'arxiv>=2.1.3',
            'googlesearch-python>=1.2.5',
            'pdfminer.six>=20240706',
            'dash_quill>=0.0.4',
            'dash_extensions>=1.0.19',
    ],
    zip_safe=True,
)