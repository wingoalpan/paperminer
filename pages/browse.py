#!/usr/bin/env python
# coding: utf-8
import dash
from dash import dcc
from dash import html
from dash import Input, Output, callback, State, ctx, clientside_callback
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import webbrowser

import paperdb as db
import webutil as util

from wingoal_utils.common import log

dash.register_page(__name__, path='/')

state = util.get_state()
taskm = util.get_taskm()

df_papers = state.table_data('papers')
df_refs = state.table_data('refs')
td_papers = state.table('papers')
td_refs = state.table('refs')

navbar = dbc.NavbarSimple(
    [
        dbc.NavItem(dbc.NavLink("Home", href="/")),
        # dbc.NavItem(dbc.NavLink("Favorites", href="/favorite")),
        dbc.NavItem(dbc.NavLink("Comment", href="/comment")),
    ],
    brand="Paper Miner",
    brand_href="#",
    color="primary",
    dark=True,
    style={'height': '40px', 'margin-bottome': '5px'}
)


layout = html.Div(
    children=[
        dbc.Row(dbc.Col(navbar, width=15),
                class_name="d-flex justify-content-center mt-2 mb-2"),
        html.Div([html.Div(html.Label("输入搜索的论文标题：", style={'font-size': 12}),
                           className='div1'),
                  html.Div(dcc.Input(id='paper_title_searching', value='attention is all you need', type='search',
                                     style={'font-size': 12, 'height': 25, 'width': 200}),
                           className='div2'),
                  # html.Div(dcc.Dropdown(['Local', 'Google'], '',
                  #                       placeholder="select site",
                  #                       id='search_site',
                  #                       style={'font-size': 12, 'width': 110, 'height': "15px", 'lineHeight': 1,
                  #                              'margin-left': 1
                  #                              }
                  #                       ),
                  #          className='div2',
                  #          style={'vertical-align': 'top', 'height': 20}),
                  html.Div(html.Button('搜索',
                                       id='btn_search', n_clicks=0,
                                       style={'font-size': 12, 'height': 25, 'lineHeight': 1,
                                              'margin-left': 1
                                              }
                                       ),
                           className='div2'),
                  html.Div(html.Button('看收藏',
                                       id='btn_filter_favorites', n_clicks=0,
                                       style={'font-size': 12, 'height': 25, 'lineHeight': 1,
                                              'margin-left': 1
                                              }
                                       ),
                           className='div3')
                  ],
                 style={"display": "flex",
                        "justify-content": "flex-start",
                        'margin-bottom': '10px'}),

        # 读论文：传递论文doclink参数
        dcc.Store(id='paper_pdf_url', data=None),
        # 查引用：操作是否结束的状态
        dcc.Store(id='analyze_paper_status', data=None),
        # 核引用：操作是否结束的状态
        dcc.Store(id='verify_ref_status', data=None),
        html.Div(children=[
            html.Div(children=util.generate_table('papers', df_papers, max_rows=50),
                     style={'marginLeft': 10,
                            'display': 'inline-block',
                            'border': 1,
                            'height': '290px', 'width': td_papers.table_width(),
                            # 'overflowY': 'scroll'
                            },
                     id='div_papers',
                     className='div1'
                     ),
            # html.Div(style={'marginLeft': 10}),
            html.Div(children=util.generate_table('refs', df_refs, max_rows=50),
                     style={'marginLeft': 10,
                            'display': 'inline-block',
                            'border': 1,
                            'height': '295px', 'width': td_refs.table_width(),
                            # 'overflowY': 'scroll'
                            },
                     id='div_refs',
                     className='div2'
                     )
        ], id='group',
            style={#'display': 'inline-block',
                   "display": "flex",
                   "justify-content": "flex-start",
                   'height': '290px',
                   "margin-bottom": "10px"}
        ),
        html.Div([
            html.Div([html.Div(html.Button('收藏', id='btn_favorite',
                                           style={'font-size': 12, 'height': 25, 'lineHeight': 1, 'position': 'relative', 'z-index': 1},
                                           n_clicks=0),
                               className='div1'),
                      html.Div(html.Button('查引用', id='btn_extract_ref',
                                           style={'font-size': 12, 'height': 25, 'lineHeight': 1, 'position': 'relative', 'z-index': 1},
                                           n_clicks=0),
                               className='div2'),
                      html.Div(html.Button('读论文', id='btn_view_paper',
                                           style={'font-size': 12, 'height': 25, 'lineHeight': 1, 'position': 'relative', 'z-index': 1},
                                           n_clicks=0),
                               className='div3'),
                      ],
                     style={
                        'display': 'flex',
                        'justify-content': 'center',
                        'width': td_papers.table_width()
                        }
                     ),
            html.Div([html.Div(html.Button('收藏', id='btn_favorite_ref',
                                           style={'font-size': 12, 'height': 25, 'lineHeight': 1, 'position': 'relative', 'z-index': 1},
                                           n_clicks=0),
                               className='div1'),
                      html.Div(html.Button('核查', id='btn_verify_ref',
                                           style={'font-size': 12, 'height': 25, 'lineHeight': 1, 'position': 'relative', 'z-index': 1},
                                           n_clicks=0),
                               className='div3'),
                      html.Div(html.Button('读论文', id='btn_view_ref',
                                           style={'font-size': 12, 'height': 25, 'lineHeight': 1, 'position': 'relative', 'z-index': 1},
                                           n_clicks=0),
                               className='div3')],
                     style={
                         'display': 'flex',
                         'justify-content': 'center',
                         'width': td_refs.table_width()
                        }
                     )
            ],
            style={'margin-top': '10px',
                   'display': 'flex',
                   'justify-content': 'flex_start',
                   }),
        html.Div([html.Div(children=td_papers.detail(), id='div_paper_detail', className='div1'),
                  html.Div(children=td_refs.detail(), id='div_ref_detail', className='div2', style={'margin-left': '15px'})],
                 style={'margin-top': '15px',
                        "display": "flex",
                        "justify-content": "flex-start",
                        }
                 ),
        dbc.Modal([
            dbc.ModalHeader("论文引用分析中"),
            dbc.ModalBody(
                html.Div([
                    html.Div(dcc.Textarea(id='id_paper_analysis_log', value='开始分析...',
                                          style={'width': '100%', 'height': '100%', 'scroll-top': '450'}),
                             style={'width': 600, 'height': 450, 'font-size': 12}
                             )
                ],
                    style={'display': 'flex', 'justify-content': 'flex_start'})
            ),
            dcc.Interval(
                id='interval_update_progress_paper',
                interval=1 * 1000,  # in milliseconds
                n_intervals=0
            ),
            dbc.ModalFooter(
                dbc.Button("关闭", id="close-modal", className="ml-auto")
            ),
        ], id="extract_ref_progress", is_open=False, size="lg", centered=True,
            style={'top': '10%', 'left': '20%', 'maxWidth': 650, 'height': 630}),

        dbc.Modal([
            dbc.ModalHeader("引用核查中"),
            dbc.ModalBody(
                html.Div([
                    html.Div(dcc.Textarea(id='id_verifying_ref_log', value='开始核查...',
                                          style={'width': '100%', 'height': '100%', 'overflow-y': 'scroll'}),
                             style={'width': 600, 'height': 450, 'font-size': 12}
                             )
                ],
                    style={'display': 'flex', 'justify-content': 'flex_start'})
            ),
            dcc.Interval(
                id='interval_update_progress_ref',
                interval=1 * 1000,  # in milliseconds
                n_intervals=0
            ),
            dbc.ModalFooter(
                dbc.Button("关闭", id="close-modal_ref", className="ml-auto")
            ),
        ], id="verifying_ref_progress", is_open=False, size="lg", centered=True,
            style={'top': '10%', 'left': '20%', 'maxWidth': 650, 'height': 630}),
    ]
)

@callback(Output('div_papers', 'children', allow_duplicate=True),
                           [Input('btn_search', 'n_clicks'),
                            State('paper_title_searching', 'value')
                            ], prevent_initial_call=True
                           )
def search_paper(n_clicks, title_for_searching):
    print(f'n_clicks={n_clicks}, searching title: {title_for_searching}')
    if title_for_searching is None:
        return dash.no_update
    print(f'searching title: {title_for_searching}')
    login = state.login
    _df_papers = db.query_dataframe(f'''SELECT p.paper_id, p.paper_name, p.publish_date, p.authors, f.login as flag
                                        FROM (SELECT * FROM papers WHERE paper_name like "%{title_for_searching}%") p 
                                        LEFT JOIN favorites f
                                        ON p.paper_id=f.paper_id and f.login="{login}"
                                        ORDER BY publish_date DESC
                                    ''')
    util.df_flag2star(_df_papers)
    return util.generate_table('papers', _df_papers, max_rows=50)


@callback(Output('div_papers', 'children', allow_duplicate=True),
          [Input('btn_filter_favorites', 'n_clicks')
           ],
          prevent_initial_call=True
          )
def filter_favorites(n_clicks):
    login = state.login
    _df_papers = db.query_dataframe(f'''SELECT p.paper_id, p.paper_name, p.publish_date, p.authors, f.login as flag
                                        FROM papers p, favorites f
                                        WHERE p.paper_id=f.paper_id and f.login="{login}"
                                        ORDER BY publish_date DESC
                                    ''')
    util.df_flag2star(_df_papers)
    return util.generate_table('papers', _df_papers, max_rows=50)


@callback(
    Output('papers', 'style_data_conditional'),
    [Input('papers', 'data')]
)
def update_paper_row_style(data):
    style_conditions = []
    for row in data:
        if row['flag'] == '☆':
            style_conditions.append({
                'if': {'row_index': data.index(row)},
                'backgroundColor': 'rgb(50,50,50)',  # 满足条件时的背景颜色
                'fontWeight': 'bold'
            })
    return style_conditions


@callback(
    Output('refs', 'style_data_conditional'),
    [Input('refs', 'data')]
)
def update_ref_row_style(data):
    style_conditions = []
    for row in data:
        if row['flag'] == '☆':
            style_conditions.append({
                'if': {'row_index': data.index(row)},
                'backgroundColor': 'rgb(50,50,50)',  # 满足条件时的背景颜色
                'fontWeight': 'bold'
            })
    return style_conditions


@callback([Output('div_paper_detail', 'children'),
                            Output('div_refs', 'children'),
                            Output('papers', 'active_cell')],
                           [Input('papers', 'active_cell'),
                            Input('papers', 'page_current'),
                            State("papers", "page_size"),
                            State("papers", "data"),
                            # Input('div_refs', 'children')
                            ])
def update_paper_related(active_cell, page_current, page_size, table_data):
    log(f'callback update_paper_related()')
    # global df_refs
    if page_current is None:
        page_current = 0
    if active_cell is None:
        active_cell = {"row": 0, "column": 0, "column_id": 'paper_id'}

    selected_index = active_cell['row'] + page_current * page_size
    row = table_data[selected_index]
    paper_id = row['paper_id']
    # 活动paper需要作为全局变量 保存
    state.current_paper = paper_id
    # log(
    #     f'selected row={selected_index}, paper_id={paper_id}, page_current={page_current}, page_size={page_size}, active_row={active_cell["row"]}')
    html_paper_detail = td_papers.detail(td_papers.get_row(paper_id))

    td_refs.update_web_table(sql_params={'paper_id': paper_id})
    df_refs = state.table_data('refs')
    refs_table = util.generate_table('refs', df_refs, max_rows=50)
    return html_paper_detail, refs_table, active_cell


@callback([Output('div_ref_detail', 'children'),
                            Output('refs', 'active_cell')],
                           [Input('refs', 'active_cell'),
                            Input('refs', 'page_current'),
                            State("refs", "page_size"),
                            State("refs", "data")])
def update_reference(active_cell, page_current, page_size, table_data):
    paper_id = state.current_paper
    if page_current is None:
        page_current = 0
    if active_cell is None:
        active_cell = {"row": 0, "column": 0, "column_id": 'ref_no'}
    selected_index = active_cell['row'] + page_current * page_size
    if len(table_data) <= 0:
        return '', active_cell
    row = table_data[selected_index]
    select_ref = td_refs.get_row({'p_paper_id': paper_id, 'ref_no': row['ref_no']})
    # print(f'update_reference(): selected_index={selected_index}, paper_id={paper_id}, select_ref={select_ref}')
    if select_ref and select_ref['paper_id']:
        state.current_ref = select_ref['paper_id']
        html_ref_detail = td_refs.detail(select_ref)
    else:
        state.current_ref = None
        html_ref_detail = td_refs.detail(select_ref, settings_index=1)
    # print(f'ref_key: {ref_key}, ref_detail: {html_ref_detail}')
    return html_ref_detail, active_cell


@callback(Output('div_papers', 'children', allow_duplicate=True),
          [Input('btn_favorite', 'n_clicks'),
           Input('papers', 'active_cell'),
           Input('papers', 'selected_rows'),
           Input('papers', 'page_current'),
           State('papers', 'page_size'),
           State('papers', 'data')],
          prevent_initial_call=True
          )
def add_favorites(n_clicks, active_cell, selected_rows, page_current, page_size, table_data):
    paper_id = state.current_paper
    log(f'callback add_favorites(): entered.')
    if not ctx.triggered:
        return dash.no_update

    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_favorite':
        rows = selected_rows if selected_rows is not None else []
        if page_current is None:
            page_current = 0
        if (active_cell is not None) and (active_cell['row'] not in rows):
            selected_index = active_cell['row'] + page_current * page_size
            rows.append(selected_index)
        if len(rows) == 0:
            log(f'No paper selected or activated')
            return dash.no_update
        for row in rows:
            data_row = table_data[row]
            paper_id = data_row['paper_id']
            login = state.login
            state.add_favorite(login, paper_id)
    return dash.no_update


@callback(Output('div_refs', 'children', allow_duplicate=True),
          [Input('btn_favorite_ref', 'n_clicks'),
           Input('refs', 'active_cell'),
           Input('refs', 'selected_rows'),
           Input('refs', 'page_current'),
           State('refs', 'page_size'),
           State('refs', 'data')],
          prevent_initial_call=True
          )
def add_favorite_refs(n_clicks, active_cell, selected_rows, page_current, page_size, table_data):
    paper_id = state.current_paper
    log(f'callback add_favorite_refs(): entered.')
    if not ctx.triggered:
        return dash.no_update

    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_favorite_ref':
        rows = selected_rows if selected_rows is not None else []
        if page_current is None:
            page_current = 0
        if (active_cell is not None) and (active_cell['row'] not in rows):
            selected_index = active_cell['row'] + page_current * page_size
            rows.append(selected_index)
        if len(rows) == 0:
            log(f'No reference paper selected or activated')
            return dash.no_update
        for row in rows:
            data_row = table_data[row]
            if not data_row['ref_id']:
                continue
            paper_id = data_row['ref_id']
            login = state.login
            state.add_favorite(login, paper_id)
    return dash.no_update


@callback(Output("extract_ref_progress", "is_open"),
          [Input('btn_extract_ref', 'n_clicks'),
           dash.dependencies.Input("close-modal", "n_clicks"),
           Input('papers', 'active_cell'),
           Input('papers', 'page_current'),
           State('papers', 'page_size'),
           State('papers', 'data')],
          [dash.dependencies.State("extract_ref_progress", "is_open")],
          prevent_initial_call=True
          )
def extract_refs(n_clicks1, n_clicks2, active_cell, page_current, page_size, table_data, is_open):
    log(f'callback extract_refs(): entered.')
    if not ctx.triggered:
        return dash.no_update

    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_extract_ref':
        if page_current is None:
            page_current = 0
        if active_cell is None:
            log('callback extract_refs(): no cell selected')
            return dash.no_update

        selected_index = active_cell['row'] + page_current * page_size
        if len(table_data) > 0:
            row = table_data[selected_index]
            paper_id = row['paper_id']
            log(f'callback extract_refs(): trying start_analyzing_paper({paper_id}) ... ')
            taskm.start_analyzing_paper(paper_id, drill=False)
            state.current_paper = paper_id
        return True
    elif ctx.triggered[0]['prop_id'].split('.')[0] == 'close-modal':
        return False
    else:
        return dash.no_update


@callback(
    [Output('id_paper_analysis_log', 'value'),
     Output("analyze_paper_status", "data")],
    [Input('interval_update_progress_paper', 'n_intervals'),
     Input("extract_ref_progress", "is_open"),
     Input("analyze_paper_status", "data")],
    prevent_initial_call=True
)
def update_paper_analysis_log(n, is_open, status):
    # 这个回调函数会根据interval-component的n_intervals输入触发
    # n_intervals是自上次页面加载以来interval-component触发的次数
    update_status = dash.no_update
    thread = taskm.thread('analyzing_paper')
    if (len(thread.todo_tasks()) > 0) or (thread.current_task() is not None):
        update_status = {'done': False}
    elif status and status['done']:
        return dash.no_update, update_status
    log_text = taskm.query_log('analyzing_paper')
    # 检查任务是否结束，若结束则更新refs数据
    if (len(thread.done_tasks()) > 0) and (len(thread.todo_tasks()) == 0) and (thread.current_task() is None):
        update_status = {'done': True}
        log(f'callback update_paper_analysis_log(): update references rows dict ... ')
        state.update_rows_dict('refs')
        return (log_text if log_text else dash.no_update), update_status
    # 任务进行中，且弹窗打开，则更新log
    if is_open:
        return log_text if log_text else dash.no_update, update_status
    else:
        raise PreventUpdate


@callback(Output("verifying_ref_progress", "is_open"),
          [Input('btn_verify_ref', 'n_clicks'),
           dash.dependencies.Input("close-modal_ref", "n_clicks"),
           Input('refs', 'active_cell'),
           Input('refs', 'selected_rows'),
           Input('refs', 'page_current'),
           State('refs', 'page_size'),
           State('refs', 'data')],
          [dash.dependencies.State("verifying_ref_progress", "is_open")],
          prevent_initial_call=True
          )
def verify_reference(n_clicks1, n_clicks2, active_cell, selected_rows, page_current, page_size, table_data, is_open):
    paper_id = state.current_paper
    log(f'callback verify_reference(): entered.')
    if not ctx.triggered:
        return dash.no_update

    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_verify_ref':
        rows = selected_rows if selected_rows is not None else []
        if page_current is None:
            page_current = 0
        if (active_cell is not None) and (active_cell['row'] not in rows):
            selected_index = active_cell['row'] + page_current * page_size
            rows.append(selected_index)
        if len(rows) == 0:
            log(f'callback verify_reference(): No reference selected or activated')
            return False
        task_schedule_result = ''
        for row in rows:
            if len(table_data) > 0:
                data_row = table_data[row]
                ref_no = data_row['ref_no']
                log(f'callback verify_reference(): trying start_verifying_reference({paper_id}->{ref_no}) ... ')
                taskm.start_verifying_reference(paper_id, ref_no)
        return True
    elif ctx.triggered[0]['prop_id'].split('.')[0] == 'close-modal_ref':
        return False
    else:
        return dash.no_update


@callback(
    [Output('id_verifying_ref_log', 'value'),
     Output('verify_ref_status', 'data')],
    [Input('interval_update_progress_ref', 'n_intervals'),
     Input("verifying_ref_progress", "is_open"),
     State('verify_ref_status', 'data')],
    prevent_initial_call=True
)
def update_verifying_ref_log(n, is_open, status):
    # 这个回调函数会根据interval-component的n_intervals输入触发
    # n_intervals是自上次页面加载以来interval-component触发的次数
    update_status = dash.no_update
    thread = taskm.thread('verifying_ref')
    if (len(thread.todo_tasks()) > 0) or (thread.current_task() is not None):
        update_status = {'done': False}
    elif status and status['done']:
        return dash.no_update, update_status
    log_text = taskm.query_log('verifying_ref')
    # 检查任务是否结束，若结束则更新refs数据
    if (len(thread.done_tasks()) > 0) and (len(thread.todo_tasks()) == 0) and (thread.current_task() is None):
        update_status = {'done': True}
        log(f'callback update_paper_analysis_log(): update references rows dict ... ')
        state.update_rows_dict('refs')
        return (log_text if log_text else dash.no_update), update_status
    # 任务进行中，且弹窗打开，则更新log
    if is_open:
        return log_text if log_text else dash.no_update, update_status
    else:
        raise PreventUpdate


@callback(Output('paper_pdf_url', 'data'),
        [Input('btn_view_paper', 'n_clicks')
     ],
    prevent_initial_call=True
)
def open_paper_pdf(n_clicks):
    url = 'https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/HintonDengYuEtAl-SPM2012.pdf'
    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_view_paper':
        if n_clicks > 0:
            paper_id = state.current_paper
            papers = state.data_dict('papers')
            doclink = papers.get(paper_id, {}).get('doclink')
            if not doclink:
                doclink = papers.get(paper_id, {}).get('weblink')
            log(f'callback open_paper_pdf(): paper_id={paper_id}, url={doclink}')
            if doclink:
                return {"url": f'/comment?paper_id={paper_id}'}
    return None


@callback(Output('paper_pdf_url', 'data', allow_duplicate=True),
        [Input('btn_view_ref', 'n_clicks')
     ],
    prevent_initial_call=True
)
def open_ref_paper_pdf(n_clicks):
    url = 'https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/HintonDengYuEtAl-SPM2012.pdf'
    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_view_ref':
        if n_clicks > 0:
            paper_id = state.current_ref
            if not paper_id:
                return None
            papers = state.data_dict('papers')
            doclink = papers.get(paper_id, {}).get('doclink')
            if not doclink:
                doclink = papers.get(paper_id, {}).get('weblink')
            log(f'callback open_ref_paper_pdf(): paper_id={paper_id}, url={doclink}')
            if doclink:
                return {"url": f'/comment?paper_id={paper_id}'}
    return None


clientside_callback(
    """
    function(url_data) {
        if (url_data && url_data.url) {
            window.open(url_data.url, '_blank'); // Open the URL in a new tab
        }
        return null;
    }
    """,
    Input('paper_pdf_url', 'data')  # Triggered when the store data changes
)

