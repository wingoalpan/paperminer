#!/usr/bin/env python
# coding: utf-8
import os
import threading
import time
import copy
import types
import pandas as pd
from dash import dcc
from dash import html
from dash import dash_table
import dash_bootstrap_components as dbc

import paperdb as db
import schedule

import wingoal_utils.common as cm
from wingoal_utils.common import log


# 参数Task必须是一个dict, 包含Task Executor需要输入参数
def gen_task_key(task):
    if not task or not isinstance(task, dict):
        return None
    keys = list(task.keys())
    keys.sort(key=lambda x: x)
    return ':'.join([str(task[key]) for key in keys])


class WebTaskThread(threading.Thread):
    thread_no = 0

    def __init__(self, task_type, executor=None, name=None):
        threading.Thread.__init__(self)
        WebTaskThread.thread_no += 1
        self.task_type = task_type
        if name:
            self.name = name
        else:
            self.name = self.task_type.replace(' ', '_') + '-' + str(WebTaskThread.thread_no)
        self.executor = executor
        self.doing_task = None
        self.to_do_list = []
        self.dones = {}
        self.status = 'idle'
        self.drill = False
        self.instruction = ''
        self.breath_interval_count = 0

    def get_thread_id(self):
        return self.ident

    def schedule_task(self, task):
        task_key = gen_task_key(task)
        if (task
                and (task not in self.to_do_list)
                and (task_key not in self.dones.keys())
                and self.status != 'terminated'):
            self.to_do_list.append(task)
            return True
        else:
            return False

    def current_task(self):
        if self.status == 'running':
            return self.doing_task
        else:
            return None

    def last_task(self):
        return self.doing_task

    def terminate(self):
        self.instruction = 'terminate'

    def enable_drill(self, drill=True):
        self.drill = drill

    def done_tasks(self):
        return copy.deepcopy(self.dones)

    def todo_tasks(self):
        return copy.deepcopy(self.to_do_list)

    def run(self):
        while True:
            if self.status == 'idle' and len(self.to_do_list) > 0:
                self.breath_interval_count = 0
                task = self.to_do_list.pop(0)
                self.doing_task = {'task': task, 'start_at': cm.time_str()}
                self.status = 'running'
                log(f'Thread: Start {self.task_type} ... {task}')
                # 支持模拟演练，方便调试/测试
                if self.drill:
                    for i in range(100):
                        progress = '{:.2%}'.format((i+1)/100)
                        log(f'Thread Drill: progress {progress}')
                        time.sleep(1)
                elif self.executor is not None:
                    self.executor(**task)
                    # schedule.analyze_paper(self.paper_id, None)
                self.doing_task['finished_at'] = cm.time_str()
                task_key = gen_task_key(task)
                self.dones[task_key] = self.doing_task
                print(f'DEBUG: dones={self.dones}')
                log(f'Thread: {self.task_type} Finished! {self.doing_task} ')
                self.status = 'idle'
            elif self.instruction == 'terminate':
                self.status = 'terminated'
                log(f'Thread: terminated [id={self.ident}, type: {self.task_type}]')
                break
            else:
                time.sleep(0.5)
                self.breath_interval_count += 1
                # Breathe every 5 minute
                if self.breath_interval_count >= 600:
                    log(f'{self.name}: I am still alive :)')
                    self.breath_interval_count = 0

    def query_log(self, task=None):
        last_task = self.last_task()
        if task is None:
            task = last_task['task'] if last_task else None
        task_key = gen_task_key(task)
        last_task_key = gen_task_key(last_task['task']) if last_task else None
        # 如果是当前正在执行的任务，end_time 可能还没有
        if task_key and task_key == last_task_key:
            start_time = last_task['start_at']
            end_time = last_task.get('end_at', None)
            return cm.query_log(start_time=start_time, end_time=end_time, thread_id=self.get_thread_id())
        # 如果是已完成任务，则设置任务start_time 和 end_time 参数
        if task_key and self.dones.get(task_key, None):
            done_task = self.dones.get(task_key, None)
            start_time = done_task['start_at']
            end_time = done_task['finished_at']
            return cm.query_log(start_time=start_time, end_time=end_time, thread_id=self.get_thread_id())
        return ''


class TableManager:
    def __init__(self, table_name, web_table_sql, rows_dict_sql, keys,
                 table_settings, column_settings, detail_settings,
                 require_sql_params=(False, False)):
        self.table_name = table_name
        self.web_table_sql = web_table_sql
        self.rows_dict_sql = rows_dict_sql
        self.require_sql_params = require_sql_params
        self.table_data = dict()
        self.rows_dict = dict()
        self.data_dict = dict()
        self.keys = keys if isinstance(keys, list) else [keys]
        self.table_settings = table_settings
        self.column_settings = column_settings
        self.detail_settings = detail_settings
        self.default_row = {}
        if not require_sql_params[0]:
            self.update_rows_dict()
        if not require_sql_params[1]:
            self.update_web_table()

    def update_rows_dict(self, sql_params=None):
        sql = self.rows_dict_sql.format(**sql_params) if self.require_sql_params[0] else self.rows_dict_sql
        self.rows_dict = db.query_rows_dict(sql)
        self.data_dict = cm.diclist2dic(self.rows_dict, self.keys)
        #print(f'data_dict len: {len(self.data_dict)}, keys={self.keys}')
        self.default_row = self.rows_dict[0]

    def update_web_table(self, sql_params=None):
        sql = self.web_table_sql.format(**sql_params) if self.require_sql_params[1] else self.web_table_sql
        rows, columns = db.query_rows(sql)
        table_data = pd.DataFrame(rows, columns=columns)
        # Flag字段转换，☆ if flag else None
        if 'flag' in columns:
            table_data['flag'] = table_data['flag'].apply(lambda x: '☆' if x else x)
        self.table_data = table_data

    def table_width(self):
        return self.table_settings.get('width', 600)

    def column_width(self, column):
        return self.column_settings.get(column, {}).get('width', 'auto')

    def column_tip(self, column):
        return self.column_settings.get(column, {}).get('tip', False)

    def get_row(self, conditions):
        if len(self.keys) == 1 and not isinstance(conditions, dict):
            row_key = conditions
        else:
            row_key = ':'.join(str(conditions[key]) for key in self.keys)
        return self.data_dict.get(row_key, {})

    def detail(self, row=None, settings_index=0):
        if row is None:
            row = self.default_row
        if row:
            detail_settings = self.detail_settings[settings_index]
            detail_width = self.table_settings.get('width', 600)
            return detail(row, detail_settings, 90, detail_width, self.table_name+'_detail')
        else:
            return 'No detail exist!'


#################################
# Task Management Module        #
#################################

def _executor_analyze_paper(paper_id, drill=False):
    if drill:
        for i in range(30):
            log(f'Drill: analyze paper {paper_id} progress {i+1}')
            time.sleep(1)
    else:
        schedule.analyze_paper(paper_id, None)


def _executor_verify_reference(paper_id, ref_no, drill=False):
    if drill:
        for i in range(30):
            log(f'Drill: verify reference {paper_id}->{ref_no} progress {i+1}')
            time.sleep(1)
    else:
        papers = state.data_dict('papers')
        ref_rows = db.table_conditions('refs', conditions={'paper_id': paper_id, 'ref_no': ref_no})
        if ref_rows:
            schedule.verify_reference(ref_rows[0], papers, None)
        else:
            log(f'Reference {ref_no} of paper {paper_id} is not found!')


def get_thread(self, task_type):
    return self.threads.get(task_type, None)


def start_analyzing_paper(self, paper_id, drill=False):
    thread = self.thread('analyzing_paper')
    if thread is not None and thread.status != 'terminated':
        if thread.schedule_task({'paper_id': paper_id, 'drill': drill}):
            return paper_id
    return None


def start_verifying_reference(self, paper_id, ref_no, drill=False):
    thread = self.thread('verifying_ref')
    if thread is not None and thread.status != 'terminated':
        if thread.schedule_task({'paper_id': paper_id, 'ref_no': ref_no, 'drill': drill}):
            return paper_id, ref_no
    return None


def schedule_task(self, task_type, task):
    thread = self.thread(task_type)
    if thread is not None and thread.status != 'terminated':
        return thread.schedule_task(task)
    return False


def terminate(self, task_type):
    thread = self.thread(task_type)
    if thread is not None:
        thread.terminate()


def query_log(self, task_type, task=None):
    thread = self.thread(task_type)
    if thread is not None:
        return thread.query_log(task)
    return ''


#################################
# Data Management Module        #
#################################

def get_table(self, table_name):
    return self.tables.get(table_name, None)


def get_table_data(self, table_name):
    tbl_man = self.tables.get(table_name, None)
    return tbl_man.table_data if tbl_man else None


def get_rows_dict(self, table_name):
    tbl_man = self.tables.get(table_name, None)
    return tbl_man.rows_dict if tbl_man else None


def get_data_dict(self, table_name):
    tbl_man = self.tables.get(table_name, None)
    return tbl_man.data_dict if tbl_man else None


def update_table_data(self, table_name):
    tbl_man = self.tables.get(table_name, None)
    if tbl_man:
        tbl_man.update_web_table()


def update_rows_dict(self, table_name):
    tbl_man = self.tables.get(table_name, None)
    if tbl_man:
        tbl_man.update_rows_dict()


def add_favorite(self, login, paper_id):
    create_at = cm.time_str()
    db.execute_sql(f'INSERT INTO favorites (login, paper_id, create_at) values("{login}", "{paper_id}", "{create_at}")')


def init_state():
    log(f'calling init_state() ...')
    _state = {}
    login = 'wingoal'    # 暂时固定为wingoal，后续支持用户管理后再完善
    table_papers = TableManager('papers',
                                f'''select p.paper_id, p.paper_name, p.publish_date, p.authors, f.login as flag
                                            FROM papers p LEFT JOIN favorites f
                                            ON p.paper_id=f.paper_id and f.login="{login}"
                                            ''',
                                'select * from papers', 'paper_id',
                                {'width': 700},
                                {'paper_id': {'width': 110},
                                 'paper_name': {'width': '40%', 'tip': True},
                                 'publish_date': {'width': '8%'}, 'authors': {'width': 'auto', 'tip': True},
                                 'flag': {'width': 30}
                                 },
                                [{
                                 'base1': [
                                     {'column': 'paper_id', 'id': 'paper_paper_id', 'name': 'Paper ID', 'height': 23},
                                     {'column': 'publish_date', 'id': 'paper_publish_date', 'name': 'Publish Date',
                                      'height': 23}
                                     ],
                                 'paper_name': {'id': 'paper_paper_name', 'name': 'Paper Name', 'height': 42,
                                                'style': {'font-weight': 'bold', 'font-size': 13}},
                                 'abstract': {'id': 'paper_abstract', 'name': 'abstract', 'height': 120},
                                 'authors': {'id': 'paper_authors', 'name': 'Authors', 'height': 42},
                                 'weblink': {'id': 'paper_weblink', 'name': 'Web Site', 'height': 42}
                                }],
                             )
    table_refs = TableManager('refs',
                              f'''SELECT r.ref_no, r.ref_id, r.ref_title, f.login as flag 
                                            FROM 
                                            (SELECT * FROM refs WHERE paper_id="<PAPER_ID>") r 
                                            LEFT JOIN 
                                            (SELECT * FROM favorites WHERE login="{login}") f
                                            ON r.ref_id = f.paper_id
                                            '''.replace('<PAPER_ID>', '{paper_id}'),
                              '''SELECT r.paper_id as p_paper_id, r.ref_no, r.ref_text, r.ref_id as paper_id, r.ref_title as paper_name, r.ref_authors,
                                                    p.authors, p.publish_date, p.abstract, p.weblink, p.doclink, p.paper_pdf
                                             FROM refs r LEFT JOIN papers p
                                             ON r.ref_id=p.paper_id;
                                        ''',
                           ['p_paper_id', 'ref_no'],
                           {'width': 700},
                           {'ref_no': {'width': '10%'}, 'ref_id': {'width': '20%'},
                            'ref_title': {'width': '70%', 'tip': True},
                            'flag': {'width': 30}
                            },
                           [{
                               'base1': [{'column': 'ref_no', 'id': 'ref_no', 'name': 'Reference No', 'height': 23,
                                          'name-width': 100, 'field-width': 150},
                                         {'column': 'paper_id', 'id': 'ref_paper_id', 'name': 'Paper ID', 'height': 23,
                                          'name-width': 60, 'field-width': 250},
                                         {'column': 'publish_date', 'id': 'ref_publish_date', 'name': 'Publish Date',
                                          'height': 23}
                                         ],
                               'paper_name': {'id': 'ref_paper_name', 'name': 'Paper Name', 'height': 40,
                                              'style': {'font-weight': 'bold', 'font-size': 13}},
                               'abstract': {'id': 'ref_abstract', 'name': 'abstract', 'height': 120},
                               'authors': {'id': 'ref_authors', 'name': 'Authors', 'height': 42},
                               'weblink': {'id': 'ref_weblink', 'name': 'Web Site', 'height': 42}
                           },
                           {
                               'base1': [
                                          {'column': 'ref_no', 'id': 'ref_no', 'name': 'Reference No', 'height': 23,
                                           'name-width': 100, 'field-width': 180},
                                          ],
                               'paper_name': {'id': 'ref_paper_name', 'name': 'Paper Name', 'height': 40,
                                               'style': {'font-weight': 'bold', 'font-size': 13}},
                               'ref_text': {'id': 'ref_text', 'name': 'ref text', 'height': 120},
                               'ref_authors': {'id': 'ref_authors', 'name': 'Authors', 'height': 42},
                           }
                           ],
                           require_sql_params=[False, True]
                           )

    paper_id = table_papers.default_row['paper_id']
    table_refs.update_web_table({'paper_id': paper_id})
    _state['login'] = login
    _state['paper_id'] = paper_id
    _state['table_papers'] = table_papers
    _state['table_refs'] = table_refs
    _state['current_paper'] = None
    _state['current_ref'] = None
    _state['selected_papers'] = []
    _state['selected_refs'] = []
    _state['analyzing_paper_status'] = {}
    _state['verifying_ref_status'] = {}
    obj = cm.dic2obj(_state)
    tables = {'papers': table_papers, 'refs': table_refs}
    setattr(obj, 'tables', tables)
    obj.table = types.MethodType(get_table, obj)
    obj.table_data = types.MethodType(get_table_data, obj)
    obj.rows_dict = types.MethodType(get_rows_dict, obj)
    obj.data_dict = types.MethodType(get_data_dict, obj)
    obj.update_table_data = types.MethodType(update_table_data, obj)
    obj.update_rows_dict = types.MethodType(update_rows_dict, obj)
    obj.add_favorite = types.MethodType(add_favorite, obj)

    return obj


def init_task_man():
    log(f'calling init_task_man() ...')
    _task_man = {}
    obj = cm.dic2obj(_task_man)

    analysis_thread = WebTaskThread('Analysis of paper', _executor_analyze_paper)
    analysis_thread.daemon = True
    analysis_thread.start()
    verifying_thread = WebTaskThread('Verifying reference', _executor_verify_reference)
    verifying_thread.daemon = True
    verifying_thread.start()

    threads = {'analyzing_paper': analysis_thread, 'verifying_ref': verifying_thread}
    setattr(obj, 'threads', threads)
    obj.thread = types.MethodType(get_thread, obj)
    obj.schedule_task = types.MethodType(schedule_task, obj)
    obj.start_analyzing_paper = types.MethodType(start_analyzing_paper, obj)
    obj.start_verifying_reference = types.MethodType(start_verifying_reference, obj)
    obj.terminate = types.MethodType(terminate, obj)
    obj.query_log = types.MethodType(query_log, obj)
    return obj


def detail(row, columns_info, name_width, field_width, detail_id):
    fields = []
    for column, cv in columns_info.items():
        if isinstance(cv, dict):
            if row.get(column, None) is None:
                continue
            fields.append(field(cv['name'], row[column], cv['id'],
                                name_width, cv['height'], field_width, cv.get('style', None)))
        elif isinstance(cv, list):
            cv = [s_col for s_col in cv if row.get(s_col['column'], None) is not None]
            num = len(cv)
            sub_field_width = int(field_width/num)
            sub_fields = [field(s_col['name'], row[s_col['column']], s_col['id'],
                                s_col.get('name-width', name_width), s_col['height'],
                                s_col.get('field-width', sub_field_width),
                                s_col.get('style', None))
                          for s_col in cv]
            fields.append(html.Div(children=sub_fields,
                                   style={
                                       'display': 'flex',
                                       'justify-content': 'flex-start',
                                       'width': field_width}
                                   )
                          )
    return html.Div(children=fields, id=detail_id)


def field(name, value, field_id, name_width, field_height, field_width, style=None):
    field_style = {'font-size': '12px'}
    if style:
        field_style.update(style)
    layout = html.Div(children=[
        html.Div([html.Label(name+':', style={'width': name_width,
                                              'font-size': '13px',
                                              'font-weight': 'bold'})],
                 className='div1',
                 style={
                     'vertical-align': 'top',
                     }),
        html.Div([dbc.Label(str(value), id=field_id, style=field_style)],
                 className='div2',
                 style={
                     'overflowY': 'auto',
                     'maxHeight': field_height,
                     'width': field_width-name_width-20,
                 })
    ], id=f'field_{field_id}',
        # className='div-paper-label-content',
        style={
            # 'display': 'inline-block',
            'margin-bottom': 5,
            'maxHeight': field_height,
            'width': field_width}
    )
    return layout


def _style_row(data, column_id, cell_style):
    style_data = {
        'width': '60px',
        'minWidth': '60px',
        'maxWidth': '200px',
        'font-size': '11px',
        'text-align': 'left',
        'vertical-align': 'middle',
    },
    if column_id == 'flag' and data['flag'] == state.login:
        return {
            'backgroundColor': 'blue',
            'fontColor': 'white',
            'fontWeight': 'bold',
            'width': '60px',
            'minWidth': '60px',
            'maxWidth': '200px',
            'font-size': '11px',
            'text-align': 'left',
            'vertical-align': 'middle',
        }
    return style_data


def generate_table(table_name, dataframe, max_rows=10):
    tbl_data = state.table(table_name)
    login = state.login
    _columns = [{'name': col, 'id': col} for col in dataframe.columns]
    style_data_conditional = [{
        'if': {
            'column_id': 'flag',  # 指定列
            'filter_query': '{flag} = ' + f'"{login}"'  # 指定条件
        },
        'backgroundColor': 'blue',  # 满足条件时的背景颜色
        'font-weight': 'bold',
        # 'font': {'color': 'white', 'weight': 'bold'}  # 满足条件时的字体颜色
    }]
    data = dataframe.to_dict('records')
    table_layout = dash_table.DataTable(
        id=table_name,
        columns=_columns,
        css=[{'selector': 'table', 'rule': 'table-layout: auto'},
             # {'selector': '.dash-spreadsheet td',
             #  'rule': '''
             #        max-height: 30px !important; min-height: 30px !important; height: 30px !important;
             #  '''
             # },
             # {'selector': '.dash-table-container', 'rule': 'height: 280px; width: 600px;'}
             ],
        style_header={
            'font-family': 'Times New Roman',  # 设置表头字体
            'font-size': '16px',  # 设置表头字体大小
            'font-weight': 'bold',  # 设置表头字体为粗体
            'text-align': 'center',  # 设置表头文本居中
        },
        style_data={
                    'width': '60px',
                    'minWidth': '60px',
                    'maxWidth': '200px',
                    'font-size': '11px',
                    'text-align': 'left',
                    'vertical-align': 'middle',
                    },
        # style_data={"hover": {"backgroundColor": "#e8f0fe"},
        #     'selector': 'row',
        #     'style': _style_row
        # },
        # style_data_conditional=style_data_conditional,
        data=data,
        page_size=max_rows,
        style_cell={
                    'height': '11px',
                    'minHeight': '11px',
                    'maxHeight': '12px',
                    'lineHeight': '1px',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                    # 'width': '110px',
                    # 'minWidth': '110px',
                    # 'maxWidth': '200p',
                    'maxWidth': 0,
                    'vertical-align': 'middle',
                    # 'whiteSpace': 'normal'
                    },
        style_table={'overflowX': 'auto',
                     # 'tableLayout': 'fixed',
                     'overflowY': 'auto',
                     'height': '280px',
                     'width': tbl_data.table_width()
        },
        style_cell_conditional=[
            {
                'if': {'column_id': col},
                'width': f'{tbl_data.column_width(col)}'
            } for col in dataframe.columns
        ],
        tooltip_data=[
            {column: {'value': str(value), 'type': 'markdown'} for column, value in row.items()
             if tbl_data.column_tip(column)}
            for row in dataframe.to_dict('records')
        ],
        tooltip_duration=None,
        fixed_rows={'headers': True, 'data': 0},
        row_selectable='multi',
        virtualization=True
    )
    return table_layout


g_state = None
g_taskm = None


def get_state():
    global g_state
    if g_state is None:
        g_state = init_state()
    return g_state


def get_taskm():
    global g_taskm
    if g_taskm is None:
        g_taskm = init_task_man()
    return g_taskm


state = get_state()