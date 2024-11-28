#!C:\Users\pypy2\AppData\Local\Programs\Python\Python311\python.exe

import os
import shutil
import sqlite3
import pandas as pd
import json as js
import wingoal_utils.common as cm

g_db_name = os.path.join(os.path.dirname(__file__), 'papers.db')


def set_db_name(db_name):
    global g_db_name
    g_db_name = os.path.abspath(db_name)


def get_db_conn():
    return sqlite3.connect(g_db_name)


def execute_sql(sql):
    conn = get_db_conn()
    cursor = conn.cursor()
    sql_ok = True
    try:
        cursor.execute(sql)
        conn.commit()
    except Exception as e:
        sql_ok = False
        print(f'Exception: {e}')
    if not sql_ok:
        cursor.executescript(sql)
    conn.close()


def init_db(sql_file):
    sql_lines = open(sql_file).readlines()
    sql = ''.join(sql_lines)
    print(sql)
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.executescript(sql)
    conn.close()


def drop_table(table_name):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(f'DROP TABLE IF EXISTS {table_name}')
    conn.commit()
    conn.close()


def table_columns(table_name):
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = [description[1] for description in cursor.fetchall()]
    conn.close()
    return columns


def query_rows(sql):
    conn = get_db_conn()
    cursor = conn.cursor()
    rows = cursor.execute(sql).fetchall()
    conn.close()
    columns = [column_info[0] for _idx, column_info in enumerate(cursor.description)]
    return rows, columns


def query_rows_dict(sql):
    rows_dict = []
    rows, columns = query_rows(sql)
    for row in rows:
        row_dict = {}
        for idx, column in enumerate(columns):
            row_dict[column] = row[idx]
        rows_dict.append(row_dict)
    return rows_dict


def table_rows(table_name):
    sql = f'select * from {table_name}'
    return query_rows(sql)


def table_rows_dict(table_name):
    sql = f'select * from {table_name}'
    return query_rows_dict(sql)


def table_conditions(table_name, conditions):
    conditions_str_list = [key + '=' + (str(val) if isinstance(val, (int, float)) else f'"{val}"')
                           for key, val in conditions.items()]
    conditions_str = ' and '.join(conditions_str_list)
    sql = f'SELECT * FROM {table_name} WHERE {conditions_str}'
    return query_rows_dict(sql)


def insert(table_name, row_dict, columns=None):
    if columns is None:
        columns = table_columns(table_name)
    if 'create_at' in columns:
        row_dict['create_at'] = cm.time_str()
    if 'update_at' in columns:
        row_dict['update_at'] = cm.time_str()
    conn = get_db_conn()
    cursor = conn.cursor()
    insert_columns = [column for column in columns if row_dict.get(column, None)]
    values = [row_dict[column] for column in insert_columns]
    # sql中非数值字段加""
    values = [str(value) if isinstance(value, (int, float)) else f'"{value}"' for value in values]
    sql = f'INSERT INTO {table_name} ({",".join(insert_columns)}) VALUES ({",".join(values)})'
    execute_sql_success = True
    try:
        cursor.execute(sql)
        #print(sql)
    except Exception as e:
        print(f'insert() Error: {e}')
        execute_sql_success = False
        pass
    conn.commit()
    conn.close()
    return execute_sql_success


def update(table_name, row_dict, keys, columns=None):
    if not isinstance(keys, list):
        keys = [keys]
    if columns is None:
        columns = table_columns(table_name)
    # 自动更新 update_at 时间
    if 'update_at' in columns:
        row_dict['update_at'] = cm.time_str()
    conn = get_db_conn()
    cursor = conn.cursor()
    update_columns = [column for column in columns if column not in keys and column in row_dict.keys()]
    row_update = [(column, row_dict[column]) for column in update_columns]
    # sql中字符串中"需要转义
    row_update = [(column, value if isinstance(value, (int, float)) or value is None else value.replace('"', '""'))
                  for column, value in row_update]
    # sql中非数值字段加""
    row_update = [(column, value if isinstance(value, (int, float)) or value is None else f'"{value}"')
                  for column, value in row_update]
    # sql中非空值字段为NULL
    row_update = [(column, value if value is not None else 'NULL')
                  for column, value in row_update]
    update_list = [f'{column}={value}' for column, value in row_update]
    conditions = {key: str(row_dict[key]) if isinstance(row_dict[key], (int, float)) else f'"{row_dict[key]}"'
                  for key in keys}
    conditions_str = ' and '.join([key + '=' + val for key, val in conditions.items()])
    sql = f'UPDATE {table_name} SET {",".join(update_list)} WHERE {conditions_str}'
    execute_sql_success = True
    try:
        #print(sql)
        cursor.execute(sql)
    except Exception as e:
        print(f'update() Error: {e}')
        execute_sql_success = False
        pass
    conn.commit()
    conn.close()
    return execute_sql_success


def insert_or_update(table_name, row_dict, key, columns=None, unique_keys=None):
    data_exist = False
    if unique_keys:
        conditions = {unique_key: row_dict[unique_key] for unique_key in unique_keys if row_dict.get(unique_key, None)}
        if len(unique_keys) != len(conditions):
            print('insert_or_update() error: Invalid values for UNIQUE keys!')
            return False
        query = table_conditions(table_name, conditions)
        if query:
            data_exist = True
            row_dict[key] = query[0][key]
    if row_dict.get(key, None):
        if table_conditions(table_name, {key: row_dict[key]}):
            data_exist = True
    if data_exist:
        return update(table_name, row_dict, key)
    else:
        return insert(table_name, row_dict)


def batch_update(table_name, rows_dict, key, update_columns=None):
    if update_columns is None:
        update_columns = table_columns(table_name)
    for row in rows_dict:
        update(table_name, row, key, update_columns)


def import_data(table_name, rows, keys, is_dict=True, overwrite=False):
    if not isinstance(keys, list):
        keys = [keys]
    columns = table_columns(table_name)
    key_indexes = {key: columns.index(key) for key in keys}
    data_rows = table_rows_dict(table_name)
    data_dict = cm.diclist2dic(data_rows, keys)
    conn = get_db_conn()
    cursor = conn.cursor()
    placeholder = ','.join(['?']*len(columns))  # example: ?, ?, ?, ?, ?, ?, ?, ?, ?
    inert_data_set = []
    update_data_set = []
    if is_dict:
        for row in rows:
            row_key = ':'.join([str(row[key]) for key in keys])
            if row_key not in data_dict.keys():
                data_row = [row.get(column, None) for column in columns]
                inert_data_set.append(data_row)
            else:
                update_data_set.append(row)
    else:
        for row in rows:
            row_key = ':'.join([str(row[key_indexes[key]]) for key in keys])
            if row_key not in data_dict.keys():
                inert_data_set.append(row)
            else:
                data_row = {column: row[idx] for idx, column in enumerate(columns)}
                update_data_set.append(data_row)
    # execute insert operation
    import_data_ok = True
    try:
        #print(js.dumps(inert_data_set, indent=2))
        cursor.executemany(f"INSERT INTO {table_name} VALUES({placeholder})", inert_data_set)
    except sqlite3.IntegrityError as e:
        print(f'import_data() Error: {e}')
        import_data_ok = False
        pass
    if overwrite:
        batch_update(table_name, update_data_set, keys)
    conn.commit()
    conn.close()
    return import_data_ok


def simple_query_sql(table_name, conditions):
    conditions_str = [f'{key}={value}' if isinstance(value, (int, float)) else f'{key}="{value}"'
                      for key, value in conditions]
    return f'select * from {table_name} where {conditions_str}'


def batch_insert_update(table_name, rows_dict, key, unique_keys=None):
    print('')


def import_excel(table_name, excel_file_name, sheet_name=None):
    tbl_papers = pd.read_excel(excel_file_name, sheet_name=sheet_name) if sheet_name else pd.read_excel(excel_file_name)
    rows = tbl_papers.to_dict('records')
    import_data(table_name, rows, True)


def export_excel(table_name, excel_file_name=None, sheet_name=None, template=None):
    if excel_file_name is None:
        excel_file_name = f'output/export_{table_name}-{cm.time_stamp()}.xlsx'
    elif not os.path.dirname(excel_file_name):
        excel_file_name = os.path.join('output', excel_file_name)
    pd_export = pd.DataFrame()
    rows = table_rows_dict(table_name)
    for row in rows:
        pd_export = pd_export._append(row, ignore_index=True)
    # 保存到excel文件
    if template and os.path.exists(template):
        shutil.copyfile(template, excel_file_name)
        with pd.ExcelWriter(excel_file_name, engine="openpyxl", mode='a', if_sheet_exists='overlay') as writer:
            pd_export.to_excel(writer, index=False)
            writer._save()
    else:
        pd_export.to_excel(excel_file_name, index=False)

