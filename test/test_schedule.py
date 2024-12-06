
import os
import sys
import argparse
import time
import pandas as pd
import json as js
import shutil
import arxiv
from googlesearch import search
import re

import wingoal_utils.common as cm
from wingoal_utils.common import (
    set_log_file,
    log,
    save_json,
    start_timer,
    time_elapse,
    time_str
)
sys.path.append('..')
from paperminer import paperdb as db
from paperminer import schedule

set_log_file(os.path.split(__file__)[-1], timestamp=True)

# db.set_db_name('../papers.db')


def test_verify_reference():
    print('to be implemented')


def test_extract_papers_references():
    schedule.extract_papers_references(2, 8)


def test_extract_references():
    # 有页眉（无横线分开），无页码 （SCAN: Learning to Classify Images without Labels）
    #paper_list = db.table_conditions('papers', {'paper_id': 'arXiv_2004.03623'})
    #paper_list = db.table_conditions('papers', {'paper_id': 'arXiv_1512.03385'})

    # 有页眉、页码, 首页有页眉 （Adversarial Feature Learning）
    #paper_list = db.table_conditions('papers', {'paper_id': 'arXiv_1605.09782'})
    # 无页眉，有页码，部分页有页底注释 （Large Scale Adversarial Representation Learning）
    #paper_list = db.table_conditions('papers', {'paper_id': 'arXiv_1907.02544'})
    # 无页眉，有页码，（2211.09117v2(MAGE- MAsked Generative Encoder to Unify Representation Learning and Image Synthesis)）
    #paper_list = db.table_conditions('papers', {'paper_id': 'arXiv_2211.09117'})
    # reference 作者和标题之间有年份
    # paper_list = db.table_conditions('papers', {'paper_id': 'arXiv_1406.2661'})
    # “References” 标记字体小，reference文本续行缩进只有5.9
    # paper_list = db.table_conditions('papers', {'paper_id': 'GS_Multitask_lea_001882'})
    # 没有缩进，通过行间距来分割不同Reference； 用分号';'来分割作者
    paper_list = db.table_conditions('papers', {'paper_id': 'GS_Ethical_Consi_29749c'})
    paper_list = db.table_conditions('papers', {'paper_id': 'arXiv_1312.6114'})

    paper = paper_list[0]
    schedule.extract_references(paper, drill=True)


def test_verify_references():
    schedule.verify_references(1, 747, drill=True)


def test_analyze_paper():
    schedule.analyze_paper('arXiv_1512.03385', None)


def main():
    print('')
    test_extract_references()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("params", nargs="*")
    args = parser.parse_args()
    start_timer()
    if len(args.params) == 0:
        log('executing function [main] ...')
        main()
    else:
        func = args.params[0]
        if func != 'main':
            set_log_file(os.path.split(__file__)[-1], suffix=func, timestamp=True)
        param_list = args.params[1:]
        log('executing function [%s] ...' % func)
        eval(func)(*param_list)
    elapse = time_elapse()[0]
    log(f'finish executing function! [{"%.6f" % elapse} seconds elapsed]')


