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
    time_stamp
)
sys.path.insert(0, '..')
import paperminer.paperdb as db


set_log_file(os.path.split(__file__)[-1], timestamp=True)


def get_workspace():
    user_dir = os.path.expanduser('~')
    paperminer_dir = os.path.join(user_dir, '.paperminer')
    if os.path.exists(paperminer_dir):
        return paperminer_dir
    else:
        return os.getcwd()


def _save_excel(rows, file_path, template=None):
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
    work_dir = get_workspace()
    generic_template = os.path.join(work_dir, 'template', 'template-generic.xlsx')
    if (file_path is not None) and not os.path.dirname(file_path):
        output_dir = os.path.join(work_dir, 'output')
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        file_path = os.path.join(output_dir, file_path)
    print(f'SQL: {sql_str}')
    if sql_str.startswith('select') or sql_str.startswith('SELECT'):
        rows = db.query_rows_dict(sql_str)
        print(f'\nTotal {len(rows)} rows returned!\n')
        if file_path and file_path.endswith('.json'):
            save_json(rows, file_path)
            print(f'Saved to file {file_path}!')
        elif file_path and file_path.endswith('.xlsx'):
            _save_excel(rows, file_path, generic_template)
            print(f'Saved to file {file_path}!')
        else:
            print(js.dumps(rows, indent=2, ensure_ascii=False))
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
    work_dir = get_workspace()
    output_dir = os.path.join(work_dir, 'output')
    if (excel_file_name is None) or not os.path.dirname(excel_file_name):
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        if excel_file_name is None:
            excel_file_name = os.path.join(output_dir, f'export_{table_name}-{time_stamp()}.xlsx')
        else:
            excel_file_name = os.path.join(output_dir, excel_file_name)

    paper_template = os.path.join(work_dir, 'template/template-export_papers.xlsx')
    ref_template = os.path.join(work_dir, 'template/template-export_refs.xlsx')
    if table_name is None:
        paper_excel_file_name = os.path.join(output_dir, f'export_papers-{time_stamp()}.xlsx')
        db.export_excel('papers', excel_file_name=paper_excel_file_name, template=paper_template)
        ref_excel_file_name = os.path.join(output_dir, f'export_refs-{time_stamp()}.xlsx')
        db.export_excel('refs', excel_file_name=ref_excel_file_name, template=ref_template)
    if table_name == 'papers':
        db.export_excel('papers', excel_file_name=excel_file_name, template=paper_template)
    if table_name == 'refs':
        db.export_excel('refs', excel_file_name=excel_file_name, template=ref_template)


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


