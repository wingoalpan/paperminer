#!C:\Users\pypy2\AppData\Local\Programs\Python\Python311\python.exe

import os
import shutil
import sys
import argparse
import json as js

import pandas as pd

from wingoal_utils.common import (
    set_log_file,
    log,
    save_json,
    start_timer,
    time_elapse,
    time_str
)
sys.path.append('..')
import paperminer.paperdb as db


set_log_file(os.path.split(__file__)[-1], timestamp=True)

# db.set_db_name('./papers.db')


def _save_excel(rows, file_path, template='template-generic.xlsx'):
    if not os.path.dirname(file_path):
        file_path = os.path.join('output', file_path)
    if (template is not None) and not os.path.dirname(template):
        template = os.path.join('template', template)
    df = pd.DataFrame()
    for row in rows:
        df = df._append(row, ignore_index=True)
    if template and os.path.exists(template):
        shutil.copyfile(template, file_path)
        with pd.ExcelWriter(file_path, engine="openpyxl", mode='a', if_sheet_exists='overlay') as writer:
            df.to_excel(writer, index=False)
            writer._save()
    else:
        df.to_excel(file_path, index=False)


def sql(sql_str, file_path=None):
    if (file_path is not None) and not os.path.dirname(file_path):
        file_path = os.path.join('output', file_path)
    print(f'SQL: {sql_str}')
    if sql_str.startswith('select') or sql_str.startswith('SELECT'):
        rows = db.query_rows_dict(sql_str)
        print(f'\nTotal {len(rows)} rows returned!\n')
        if file_path and file_path.endswith('.json'):
            save_json(rows, file_path)
            print(f'Saved to file {file_path}!')
        elif file_path and file_path.endswith('.xlsx'):
            _save_excel(rows, file_path)
            print(f'Saved to file {file_path}!')
        else:
            print(js.dumps(rows, indent=2))
    else:
        db.execute_sql(sql_str)


def sqlf(sql_file, file_path=None):
    if not os.path.exists(sql_file):
        log(f'Error in sqlf(): sql file {sql_file} not exist')
        return
    with open(sql_file, 'rt', encoding='utf-8') as f_sql:
        sql_str = f_sql.read()
    sql(sql_str, file_path)


def export(table_name=None, excel_file_name=None):
    if table_name is None:
        db.export_excel('papers', template='template/template-export_papers.xlsx')
        db.export_excel('refs', template='template/template-export_refs.xlsx')
    if table_name == 'papers':
        db.export_excel('papers', excel_file_name=excel_file_name, template='template/template-export_papers.xlsx')
    if table_name == 'refs':
        db.export_excel('refs', excel_file_name=excel_file_name, template='template/template-export_refs.xlsx')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("params", nargs="*")
    args = parser.parse_args()
    start_timer()
    if len(args.params) == 0:
        log('no operation selected!')
    else:
        func = args.params[0]
        if func != 'main':
            set_log_file(os.path.split(__file__)[-1], suffix=func, timestamp=True)
        param_list = args.params[1:]
        log('executing function [%s] ...' % func)
        eval(func)(*param_list)
    elapse = time_elapse()[0]
    log(f'finish executing function! [{"%.6f" % elapse} seconds elapsed]')


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


