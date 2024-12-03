
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

sys.path.insert(0, '..\\..')
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
import paperdb as db
import webutil as util

db.set_db_name('../papers.db')


def test_log():
    _paper_id='arXiv_1512.03385'
    analyzing_paper_id = util.start_analyzing_paper(_paper_id)
    for i in range(120):
        log_text = util.get_paper_analysis_log()
        print(f'*** logs ***:\n{log_text}\n==== logs ====')
        time.sleep(1)


def test_gen_task_key():
    task1 = {'paper_id': 'arXiv_2005.19071', 'ref_no': 32}
    task2 = {'ref_no': 32, 'paper_id': 'arXiv_2005.19071'}
    print(f'task1={task1}  key={util.gen_task_key(task1)}')
    print(f'task2={task2}  key={util.gen_task_key(task2)}')


def test_start_analyzing_paper():
    task = {'paper_id': 'arXiv_2005.1907', 'drill': True}
    thread = util.state.thread('analyzing_paper')
    if thread:
        thread.schedule_task(task)
        for i in range(16):
            print(f'*** logs ***\n{thread.query_log(task)}\n=== logs ===\n')
            time.sleep(2)
    task = {'paper_id': 'arXiv_2112.09573', 'drill': True}
    thread = util.state.thread('analyzing_paper')
    if thread:
        thread.schedule_task(task)
        for i in range(16):
            print(f'*** logs ***\n{thread.query_log(task)}\n=== logs ===\n')
            time.sleep(2)


def test_start_verify_reference():
    util.state.start_verifying_reference('arXiv_2005.1907', 20, drill=True)
    for i in range(20):
        print(f'*** logs ***\n{util.state.query_log("verifying_ref")}\n=== logs ===\n')
        time.sleep(2)
    util.state.terminate('verifying_ref')
    time.sleep(1)


def test_dic2obj():
    dic={'paper_id': 'arX9v_2005.1907', 'detail': {'title': 'about LLM Models', 'citations':359}}
    obj=cm.dic2obj(dic)
    print(f'paper_id = {obj.paper_id}, title={obj.detail.title}, citations={obj.detail.citations}')


def test_query_log():
    print(f'\n---------test_query_log()--------\n')
    thread = util.state.thread('analyzing_paper')
    task = {'paper_id': 'arXiv_2005.1907', 'drill': True}
    print(f'*** logs ***\n{thread.query_log(task)}\n=== logs ===\n')
    task = {'paper_id': 'arXiv_2112.09573', 'drill': True}
    print(f'*** logs ***\n{thread.query_log(task)}\n=== logs ===\n')
    thread.terminate()
    time.sleep(1)


def test_lineage_between():
    # src, target = 'arXiv_2307.08702', 'arXiv_1905.01278'
    src, target = 'arXiv_2307.08702', 'arXiv_1505.01749'
    print(util.get_lineage_between(src, target))


def main():
    print('')
    test_lineage_between()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("params", nargs="*")
    args = parser.parse_args()
    start_timer()
    if len(args.params) == 0:
        set_log_file(os.path.split(__file__)[-1], timestamp=True)
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


