#!C:\Users\pypy2\AppData\Local\Programs\Python\Python311\python.exe

from __future__ import print_function
from setuptools import setup, Command
from setuptools.command.install import install
import os
import shutil


class PostInstallCommand(install):
    """Post-installation for installation mode."""
    def run(self):
        install.run(self)
        move_config_db(self)


def move_config_db(self):
    user_dir = os.path.expanduser('~')
    paperminer_dir = os.path.join(user_dir, '.paperminer')
    if not os.path.exists(paperminer_dir):
        os.mkdir(paperminer_dir)
    # 安装配置文件config.json
    config_file = os.path.join(paperminer_dir, 'config.json')
    if not os.path.exists(config_file):
        print('installing config.json ...')
        shutil.move('paperminer/config.json', config_file)
    # 安装配置文件database
    db_file = os.path.join(paperminer_dir, 'db/papers.db')
    if not os.path.exists(db_file):
        db_dir = os.path.join(paperminer_dir, 'db')
        if not os.path.exists(db_dir):
            os.mkdir(db_dir)
        print('installing db/papers.db ...')
        shutil.move('paperminer/db/papers.db', db_file)
    # 安装导出模版文件 template/*
    template_dir = os.path.join(paperminer_dir, 'template')
    if not os.path.exists(template_dir):
        os.mkdir(template_dir)
    template_files = os.listdir('paperminer/template')
    for template_file in template_files:
        target_file = os.path.join(template_dir, template_file)
        if not os.path.exists(target_file):
            print('installing template/{template_file} ...')
            shutil.move(f'paperminer/template/{template_file}', target_file)
    # 准备输出目录 output
    output_dir = os.path.join(paperminer_dir, 'output')
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)


setup(
    name="paperminer",
    version="0.1.0",
    author="Wingoal",  # 作者名字
    author_email="panwingoal@gmail.com",
    description="Paper lineage miner and a paper viewer.",
    license="MIT",
    url="https://github.com/wingoalpan/paperminer",  # github地址或其他地址
    packages=['paperminer', 'paperminer.db', 'paperminer.template', 'test',
              'paperminer.web', 'paperminer.web.pages', 'paperminer.web.assets'],
    package_dir={'paperminer': 'paperminer',
                 'paperminer.db': 'paperminer/db',
                 'paperminer.template': 'paperminer/template',
                 'paperminer.web': 'paperminer/web',
                 'paperminer.web.pages': 'paperminer/web/pages',
                 'paperminer.web.assets': 'paperminer/web/assets',
                 'test': 'test'
                 },
    data_files=[],
    package_data={'': ['*.json', 'template/*.xlsx',
                       'db/*.sql', 'db/papers.db',
                       'web/assets/*.css', 'web/assets/*.js']
                  },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'paperminer=paperminer.web.webapp:start',
            'dbsql=paperminer.dbsql:main',
        ]
    },
    cmdclass={
        'install': PostInstallCommand
    },
    classifiers=[
        "Environment :: Windows Environment",
        'Intended Audience :: Academic Researchers or Technical Experts',
        'License :: MIT License',
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
            'wingoal_utils@https://github.com/wingoalpan/wingoal_utils/tarball/main'
    ],
    zip_safe=True,
)