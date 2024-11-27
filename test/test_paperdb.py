
import os
import sys
import argparse
import json as js

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


set_log_file(os.path.split(__file__)[-1], timestamp=True)

db.set_db_name('../papers.db')


def main():
    print('')
    insert_or_update()


def insert_or_update():
    rows = [{'paper_id': 'arXiv_2005.12320', 'ref_no': 7, 'ref_id': 'arXiv_2002.05709'},
            {'paper_id': 'arXiv_2005.12320', 'ref_no': 8, 'ref_id': 'arXiv_2003.04297'},
            {'paper_id': 'arXiv_2005.12320', 'ref_no': 12, 'ref_id': 'arXiv_1708.04552'},
            {'paper_id': 'arXiv_2005.12320', 'ref_no': 18, 'ref_id': 'arXiv_1911.05722'},
            {'paper_id': 'arXiv_2005.12320', 'ref_no': 20, 'ref_id': 'arXiv_1905.09272'},
            {'paper_id': 'arXiv_2005.12320', 'ref_no': 25, 'ref_id': 'arXiv_1412.6980'},
        ]
    for row in rows:
        db.insert_or_update('refs', row, 'id', unique_keys=['paper_id', 'ref_no'])

    rows = [{'id': 659, 'paper_id': 'arXiv_2005.12320', 'ref_no': 26, 'ref_id': 'arXiv_1312.6114'},
            {'id': 671, 'paper_id': 'arXiv_2005.12320', 'ref_no': 38, 'ref_id': 'arXiv_1807.03748'},
            {'id': 673, 'paper_id': 'arXiv_2005.12320', 'ref_no': 40, 'ref_id': 'arXiv_1511.06434'},
            {'id': 679, 'paper_id': 'arXiv_2005.12320', 'ref_no': 46, 'ref_id': 'arXiv_2001.07685'},
            {'id': 681, 'paper_id': 'arXiv_2005.12320', 'ref_no': 48, 'ref_id': 'arXiv_1906.05849'},
            {'id': 692, 'paper_id': 'arXiv_2005.12320', 'ref_no': 59, 'ref_id': 'arXiv_1506.02351'},
        ]
    for row in rows:
        db.insert_or_update('refs', row, 'id')


def table_rows_conditions():
    rows = db.table_conditions('refs', {'paper_id': 'arXiv_1605.09782', 'ref_no': 35})
    print(js.dumps(rows, indent=2))


def query_sql():
    sql = 'select * from papers where paper_id in ("2002.05709","2003.04297","1708.04552","1911.05722","1905.09272","1412.6980","1312.6114","1807.03748","1511.06434","2001.07685","1906.05849","1506.02351")'
    rows = db.query_rows_dict(sql)
    print(js.dumps(rows, indent=2))


def execute_sql():
    sql = 'delete from papers where paper_id in ("2002.05709","2003.04297","1708.04552","1911.05722","1905.09272","1412.6980","1312.6114","1807.03748","1511.06434","2001.07685","1906.05849","1506.02351")'
    db.execute_sql(sql)


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


