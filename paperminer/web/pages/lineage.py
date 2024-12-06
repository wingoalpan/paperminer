#!/usr/bin/env python
# coding: utf-8
import copy

import dash
import pandas as pd
from dash import dcc
from dash import html
from dash import Input, Output, callback, State, ctx, clientside_callback
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from dash_extensions import EventListener
import json as js

import paperdb as db
import webutil as util

from wingoal_utils.common import log

dash.register_page(__name__, path='/lineage')

state = util.get_state()

navbar = dbc.NavbarSimple(
    [
        dbc.NavItem(dbc.NavLink("Home", href="/")),
        dbc.NavItem(dbc.NavLink("Lineage", href="/lineage")),
    ],
    brand="Paper Miner",
    brand_href="#",
    color="primary",
    dark=True,
    style={'height': '40px', 'margin-bottom': '5px'}
)


# 根据paper_id 生成网页上的 paper显示节点
def generate_paper_node(paper_id):
    if paper_id is None:
        return html.Div()
    paper = state.get_paper(paper_id)
    paper_name = paper.get('paper_name', '') if paper else ""
    paper_name_show = paper_name if len(paper_name) < 20 else (paper_name[:17] + '...')
    paper_node = html.Div([
        # paper_id
        html.Div(
            html.Label(f'{paper_id}:',
                       # className=' tooltip',
                       style={'font-weight': 'bold', 'font-size': 10,
                              'max-height': 15, 'display': 'inline-block'}
                       ),
            className='div-ellipsis',
            style={'margin-bottom': '2px'}
        ),
        # paper_name
        html.Div(
            html.Label(f'{paper_name_show}',
                       style={'max-height': 25}),
            className='div-ellipsis'
        ),
    ], className='div-border ml-5 mr-5 mt-1 mb-1',
        title=f'{paper_id} - {paper_name}',
        style={'width': 110, 'height': 40, 'background-color': 'black'})
    return paper_node


# 根据paper列表，生成多个paper显示节点的列表
def generate_paper_nodes(paper_ids):
    if paper_ids is None or len(paper_ids) == 0:
        return html.Div()
    paper_nodes = []
    for paper_id in paper_ids:
        paper_node = generate_paper_node(paper_id)
        paper_nodes.append(paper_node)
    return paper_nodes


def generate_lineage_graph(src_link, target_link):
    # if target is None:
    #     return html.Div()
    MAX_SRC_LINK_DISPLAY = 5
    MAX_TGT_LINK_DISPLAY = 4
    # 无connection 或 target 的target_link是无效的
    if src_link is None or len(src_link) < 2:
        target_link = None
    src = src_link[0] if src_link is not None else None
    connection = src_link[-1] if src_link is not None and len(src_link) >= 2 else None
    target = connection if target_link is None else target_link[-1]
    src_inter_link = src_link[1:-1] if (src_link is not None) and (len(src_link) > 2) else None
    target_inter_link = target_link[1:-1] if (target_link is not None) and (len(target_link) > 2) else None
    src_link_show = src_inter_link \
        if (src_inter_link is None) or (len(src_inter_link) <= MAX_SRC_LINK_DISPLAY)\
        else src_inter_link[:MAX_SRC_LINK_DISPLAY]
    target_link_show = target_inter_link \
        if (target_inter_link is None) or (len(target_inter_link) <= MAX_TGT_LINK_DISPLAY)\
        else target_inter_link[:MAX_TGT_LINK_DISPLAY]
    src_show = src
    target_show = None if target_link is None else target

    lineage_graph_display = 'none' if src is None else None
    lineage_link_display = 'none' if target is None else None
    lineage_graph_style = {'width': '100%', 'display': 'none'} if lineage_graph_display == 'none' else {'width': '100%'}
    lineage_link_style = {'width': '100%', 'display': 'none'} if lineage_link_display == 'none' else {'width': '100%'}
    slider1_display = 'none' if src_inter_link is None or len(src_inter_link) <= MAX_SRC_LINK_DISPLAY else None
    slider2_display = 'none' if target_inter_link is None or len(target_inter_link) <= MAX_TGT_LINK_DISPLAY else None
    slider1_max = max(0, len(src_inter_link) - MAX_SRC_LINK_DISPLAY) if src_inter_link is not None else 0
    slider2_max = max(0, len(target_inter_link) - MAX_TGT_LINK_DISPLAY) if target_inter_link is not None else 0
    slider1_width = 110 * min(len(src_link_show), MAX_SRC_LINK_DISPLAY) if src_link_show is not None else 0
    slider2_width = 110 * min(len(target_link_show), MAX_TGT_LINK_DISPLAY) if target_link_show is not None else 0
    slider1_div_style = {'width': slider1_width}
    slider2_div_style = {'width': slider2_width}
    if slider1_display == 'none' and slider2_display == 'none':
        slider1_div_style['display'] = 'none'
        slider2_div_style['display'] = 'none'
    elif slider1_display == 'none' and slider2_display != 'none':
        slider1_div_style['visibility'] = 'hidden'
    elif slider1_display != 'none' and slider2_display == 'none':
        slider2_div_style['display'] = 'none'

    title = '论文关系链: ' if (src is not None) and (target is not None) else '未查到两篇论文血缘关系！'
    debug_info = {"lineage_graph_display": lineage_graph_display,
                  "lineage_link_display": lineage_link_display,
                  "slider1_display": slider1_display,
                  "slider2_display": slider2_display,
                  'slider1_max': slider1_max,
                  'slider2_max': slider2_max,
                  'slider1_width': slider1_width,
                  'slider2_width': slider2_width,
                  'src': src,
                  'target': target
                  }
    print(f'DEBUG: {js.dumps(debug_info, indent=2)}')
    lineage_graph = html.Div([
        html.Div(html.Label(title), className='mr-10', style={'width': 90}),
        html.Div([
            html.Div([
                html.Div([generate_paper_node(src_show)],
                         className='mt-1',
                         style={'background-color': 'gray'}, ),
                html.Div(generate_paper_nodes(src_link_show),
                         className='div-flex-left mt-1',
                         style={'background-color': 'blue'},
                         id='id_citations_link_src'),
                html.Div([generate_paper_node(connection)],
                         className='mt-1',
                         style={'background-color': 'gray'}),
                html.Div(generate_paper_nodes(target_link_show),
                         className='div-flex-left mt-1',
                         style={'background-color': 'blue'},
                         id='id_citations_link_target'),
                html.Div([generate_paper_node(target_show)],
                         className='mt-1',
                         style={'background-color': 'gray'}),
            ], className='div-flex-left mb-2'),
            # 添加滑动条
            html.Div([
                html.Div(style={'width': 110}),
                html.Div(
                    html.Div(
                        dcc.Slider(id='id-citations-slider',
                                   min=0, max=slider1_max, step=1, value=0,
                                   marks={0: '0', slider1_max: str(slider1_max)}
                                   ),
                        style={'width': slider1_width/2}
                    ),
                    className='div-flex-center',
                    style=slider1_div_style
                ),
                html.Div(style={'width': 110}),
                html.Div(
                    html.Div(
                        dcc.Slider(id='id-refs-slider',
                                   min=0, max=slider2_max, step=1, value=0,
                                   marks={0: '0', slider2_max: str(slider2_max)}
                                   ),
                        style={'width': slider2_width / 2}
                    ),
                    className='div-flex-center',
                    style=slider2_div_style
                )
            ], className='div-flex-left'),
        ], className='ml-10 mt-2', style=lineage_link_style
        ),
    ], className='div-flex-left',
        style=lineage_graph_style)
    return lineage_graph


def gen_citations_or_references_table(paper_id, opt='citations', lineage_explore=None):
    lineage_graph = state.lineage_graph
    relations = lineage_graph.get(paper_id, {}).get(opt, None) if (paper_id is not None) else None
    table_config = {'table_width': 500,
                    'table_height': 300,
                    'columns': {
                        'paper_id': {'width': 130},
                        'paper_name': {'width': 'auto', 'tip': False},
                        'ref_no': {'width': 50},
                        'flag': {'width': 40}
                    }}
    page_size = 50
    page_current = None
    active_cell = None
    if relations:
        visit_traces = lineage_explore.get('visit_traces') if lineage_explore is not None else []
        pos = lineage_explore.get('pos') if lineage_explore is not None else 0
        pos = (pos - 1) if opt == 'citations' else (pos + 1)
        target = visit_traces[pos] if (pos >= 0) and (pos < len(visit_traces)) else None
        flag_refs = visit_traces
        related_papers = [(lineage_graph.get(relation[0], {}).get('paper', None), relation[1]) for relation in relations]
        data = [[paper['paper_id'], paper['paper_name'], ref_no, '☆' if paper['paper_id'] in flag_refs else None]
                for paper, ref_no in related_papers if paper is not None]
        df_table = pd.DataFrame(data, columns=['paper_id', 'paper_name', 'ref_no', 'flag'])
        if target is not None:
            for i, row in enumerate(data):
                if row[0] == target:
                    if i < page_size:
                        active_cell = {'row': i, 'column': 0}
                    else:
                        page_current = i // page_size
                        active_cell = {'row': i % page_size, 'column': 0}
    else:
        df_table = pd.DataFrame([], columns=['paper_id', 'paper_name', 'ref_no', 'flag'])
    table_layout = util.create_table_layout(f'table_{opt}', df_table, table_config,
                                            max_rows=page_size,
                                            virtualization=False, row_selectable=False,
                                            page_current=page_current,
                                            active_cell=active_cell)
    return table_layout


def gen_select_target_table(target_match_pat, src):
    table_config = {'table_width': 620,
                    'table_height': 420,
                    'column_settings': {
                        'paper_id': {'width': 110},
                        'paper_name': {'width': '45%', 'tip': True},
                        'publish_date': {'width': '10%'},
                        'authors': {'width': 'auto', 'tip': True}
                    }}
    if target_match_pat is not None and src is not None:
        df_select_target = db.query_dataframe(f'''SELECT paper_id, paper_name, publish_date, authors
                                        FROM papers WHERE paper_name like "%{target_match_pat}%"
                                                    AND paper_id != "{src}"
                                        ORDER BY publish_date DESC
                                    ''')
    else:
        df_select_target = pd.DataFrame([], columns=['paper_id', 'paper_name', 'publish_date', 'authors'])

    return util.create_table_layout(f'table_select_target', df_select_target, table_config, max_rows=50)


def gen_visit_traces_layout(lineage_explore):
    core_paper = lineage_explore.get('core')
    visit_traces = lineage_explore.get('visit_traces')
    pos = lineage_explore.get('pos')
    cur_paper = visit_traces[pos]
    children = []
    for i, paper_id in enumerate(visit_traces):
        if i > 0:
            children.append(
                html.Div('->',
                         className='ml-5 mr-5', style={'display': 'flex', 'align-items': 'center', 'height': 25})
            )
        style = {'display': 'flex', 'align-items': 'center', 'height': 25, 'margin-left': 5, 'margin-right': 5}
        if paper_id == core_paper:
            style['font-weight'] = 'bold'
        if paper_id == cur_paper:
            style['border'] = '1px solid'
            style['background-color'] = 'rgb(50,50,50)'
        children.append(
            html.Div(paper_id,
                     style=style)
        )
    return children


def gen_current_paper_detail(paper_id):
    lineage_graph = state.lineage_graph
    paper = lineage_graph.get(paper_id, {}).get('paper', None)
    if paper is None:
        return None
    paper = copy.deepcopy(paper)
    paper['abstract'] = paper['abstract'].replace('\n', ' ')
    columns_info = {
        'paper_id': {'id': 'paper_paper_id', 'name': 'Paper ID', 'height': 23},
        'publish_date': {'id': 'paper_publish_date', 'name': 'Publish Date', 'height': 23},
        'paper_name': {'id': 'paper_paper_name', 'name': 'Paper Name', 'height': 45,
                       'style': {'font-weight': 'bold', 'font-size': 13}},
        'abstract': {'id': 'paper_abstract', 'name': 'Abstract', 'height': 160},
        'authors': {'id': 'paper_authors', 'name': 'Authors', 'height': 60},
        # 'weblink': {'id': 'paper_weblink', 'name': 'Web Site', 'height': 42}
    }
    return util.detail(paper, columns_info, 90, 450, 'id_current_paper_detail')


def gen_paper_summary(paper_id, layout_id):
    lineage_graph = state.lineage_graph
    paper = lineage_graph.get(paper_id, {}).get('paper', None)
    if paper is None:
        return None
    columns_info = {
        'paper_id': {'id': 'paper_paper_id', 'name': 'Paper ID', 'height': 23},
        'paper_name': {'id': 'paper_paper_name', 'name': 'Paper Name', 'height': 50,
                       'style': {'font-weight': 'bold', 'font-size': 13}},
        'abstract': {'id': 'paper_abstract', 'name': 'Abstract', 'height': 120},
        # 'authors': {'id': 'paper_authors', 'name': 'Authors', 'height': 40},
    }
    return util.detail(paper, columns_info, 90, 750, layout_id)


def create_lineage_relations(paper_id, target=None):
    log(f'create_lineage_relations(): entered.')
    lineage_relations = {'core': paper_id}
    if target is not None:
        lineage_relations['src_link'] = util.get_lineage_between(paper_id, target)
        print(f'DEBUG: create_lineage_relations(): src={paper_id}, target={target}, src_link={lineage_relations["src_link"]} ')
    return lineage_relations


def create_lineage_explore(paper_id):
    lineage_explore = {'core': paper_id, 'visit_traces': [paper_id], 'pos': 0}
    return lineage_explore


layout = html.Div([
    dcc.Location(id='url_lineage', refresh=False),
    # core, target, src_link, target_link
    dcc.Store(id='store_lineage_relations', data=None),
    # core, visit_traces, pos
    dcc.Store(id='store_lineage_explore', data=None),
    dcc.Store(id='has_dblclick_on_citations', data=None),
    dcc.Store(id='has_dblclick_on_references', data=None),

    dcc.Store(id='lineage_paper_pdf_url', data=None),

    # 论文谱系查询
    dbc.Row(dbc.Col(navbar, width=15),
            class_name="d-flex justify-content-center mt-2 mb-2"),
    html.Div([
        # 源论文 和 目标论文选择
        html.Div([
            html.Div([
                html.Div(html.Label('Source Paper:'), className='mr-10', style={'width': 90}),
                html.Div(html.Label(state.current_paper, id='id_src_paper'),
                         className='div-border ml-5',
                         style={'width': 350})
            ], className='div-flex-left', style={'width': '40%', 'height': 25}),
            html.Div([
                html.Div(html.Label('Target Paper:'), className='mr-10'),
                html.Div(html.Label('', id='id_tgt_paper'),
                         className='div-border ml-10',
                         style={'width': 350}),
            ], className='div-flex-left', style={'width': '40%', 'height': 35}),
            html.Div([
                html.Div(dcc.Input('Attention is all you need', id='id_tgt_match_pat',
                                   style={'width':150, 'height': 25, 'margin-left': 10})),
                html.Div(html.Button('选择', id='btn_select_tgt', style={'height': 25, 'margin-left': 1}))
            ], className='div-flex-left'),
        ], className='div-flex-left',
            style={
                  'width': '1200px', 'height': 30}
        ),
        # 论文关系链
        html.Div(id='id_lineage'),
    ], className='mb-10'),
    # 论文访问轨迹记录
    html.Div([
        html.Div(
            html.Label('Visit Traces:'),
            className='mr-5', style={'display': 'flex', 'align-items': 'center', 'width': 90}
        ),
        html.Div('<Paper View Tracks>',
                 id='id_visit_traces',
                 className='div-flex-left mb-2 ml-5'
                 )
    ], className='div-flex-left mb-10', style={'width': '100%', 'height': 25}),
    # 论文关系区
    html.Div([
        html.Div([
            html.Div([
                html.Div(
                    EventListener(
                        id='dblclick_citations',
                        events=[{'event': 'dblclick', 'props': ['srcElement.innerText', 'pageX']}],
                        children=gen_citations_or_references_table(None, opt='citations')
                    ),
                    id='id_paper_citations',
                    style={'display': 'inline-block', 'height': 315, 'margin-bottom': '1px'}
                ),
                html.Div([
                    html.Button('读论文', id='btn_read_citation',
                                className='centered-button mr-10',
                                style={'width': 80, 'height': 25}),
                ], className='div-flex-center', style={'height': 25, 'margin-top': '1px'})
            ], className='div1 div-border ml-10 mr-5',
                style={'width': '40%', 'height': 370}
            ),
            # 当前论文概要信息
            html.Div([
                html.Div([], id='id_current_paper',
                         className='div-flex-left mt-2 mb-2',
                         style={'height': 330, 'margin-bottom': '1px'}),
                # 论文访问 向前/向后 按钮
                html.Div([
                    html.Button('<<', id='btn_back',
                                className='centered-button mr-5',
                                style={'width': 80, 'height': 25}),
                    html.Button('>>', id='btn_forward',
                                className='centered-button ml-5',
                                style={'width': 80, 'height': 25}),
                    html.Button('读论文', id='btn_read_cur_paper',
                                className='centered-button ml-20',
                                style={'width': 80, 'height': 25}),
                ],
                    className='div-flex-center',
                    style={'height': 25, 'margin-top': '1px'}),
            ], className='div-border ml-10 mr-10',
                style={'width': '30%', 'height': 370}),
            html.Div([
                html.Div(
                    EventListener(
                        id='dblclick_references',
                        events=[{'event': 'dblclick', 'props': ['srcElement.innerText', 'pageX']}],
                        children=gen_citations_or_references_table(None, opt='references')
                    ),
                    id='id_paper_refs',
                    style={'display': 'inline-block', 'height': 315, 'margin-bottom': '1px'}),
                html.Div([
                    html.Button('读论文', id='btn_read_reference',
                                className='centered-button mr-10',
                                style={'width': 80, 'height': 25}),
                ], className='div-flex-center', style={'height': 25, 'margin-top': '1px'}),
            ], className='div3 div-border ml-5 mr-5',
                style={'width': '40%', 'height': 370}
            )
        ], className='div-flex-left', style={'width': '100%', 'height': 370}),
    ], className='mb-10'),
    html.Div([
        html.Div(id='div_summary_citation', className='div-border mr-5', style={'width': 760}),
        # html.Div(id='div_dummy', style={'width': 465, 'height': 150}),
        html.Div(id='div_summary_reference', className='div-border ml-5', style={'width': 760})
    ], id='id_paper_detail',
             className='div-flex-left-top',
             style={'width': '100%'}),
    dbc.Modal([
        dbc.ModalHeader("选择关联论文"),
        dbc.ModalBody(
            html.Div([
                html.Div(gen_select_target_table(None, None),
                         id='id_select_paper_list',
                         className='div1',
                         style={'display': 'inline-block', 'width': 620, 'height': 450, 'font-size': 12}
                         )
            ], className='div-flex-center',
                style={'width': 620, 'height': 450, })
        ),
        dbc.ModalFooter(
            dbc.Button("关闭", id="btn_close_modal_select_target", className="ml-auto")
        ),
    ], id="id_select_target_dialog", is_open=False, size="lg", centered=True,
        style={'top': '10%', 'left': '20%', 'maxWidth': 650, 'height': 630}),

],

)


@callback([Output("id_select_target_dialog", "is_open", allow_duplicate=True),
           Output('id_select_paper_list', 'children')],
          [Input('btn_select_tgt', 'n_clicks'),
           Input('id_tgt_match_pat', 'value'),
           Input('store_lineage_relations', 'data')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True
)
def select_lineage_target(n_clicks, target_match_pat, lineage_relations):
    log(f'callback select_lineage_target(): entered.')
    if not ctx.triggered:
        return dash.no_update, dash.no_update

    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_select_tgt':
        paper_id = lineage_relations.get('core')
        table_select_list = gen_select_target_table(target_match_pat, paper_id)
        return True, table_select_list
    return dash.no_update, dash.no_update


@callback([Output("id_select_target_dialog", "is_open", allow_duplicate=True),
           Output('id_tgt_paper', 'children', allow_duplicate=True),
           Output('id_tgt_paper', 'title', allow_duplicate=True),
           Output('store_lineage_relations', 'data', allow_duplicate=True)],
          [Input('btn_close_modal_select_target', 'n_clicks'),
           Input('store_lineage_relations', 'data'),
           Input('table_select_target', 'active_cell'),
           Input('table_select_target', 'page_current'),
           State('table_select_target', 'page_size'),
           State('table_select_target', 'data')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True
)
def on_selected_target(n_clicks, lineage_relations, active_cell, page_current, page_size, table_data):
    log(f'callback on_selected_target(): entered.')
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_close_modal_select_target':
        row = util.web_table_row(active_cell, page_current, page_size, table_data)
        target = row.get('paper_id', None) if row else None
        if target is not None:
            paper = state.get_paper(target)
            paper_name = paper.get('paper_name') if paper else None
            paper_name_show = paper_name if paper_name is not None and len(paper_name) < 45\
                else (paper_name[:42] + '...')
            log(f'callback on_selected_target(): selected target={target}')
            src = lineage_relations.get('core')
            return False, f'{target} - {paper_name_show}', f'{target} - {paper_name}', create_lineage_relations(src, target)
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update


@callback(
    [Output('store_lineage_relations', 'data', allow_duplicate=True),
     Output('store_lineage_explore', 'data', allow_duplicate=True)],
    [Input('url_lineage', 'pathname'),
     Input('url_lineage', 'search')],
    [State('url_lineage', 'href')],
    prevent_initial_call=True,
    suppress_callback_exceptions=True
)
def get_data_from_url(pathname, search, href):
    log(f'callback get_data_from_url(): entered.')
    # 提取查询参数
    if search:
        query = dict([param.split('=') for param in search[1:].split('&')])
        paper_id = query.get('paper_id', None)
    else:
        paper_id = state.current_paper
    log(f'callback get_data_from_url(): paper_id={paper_id}')
    # return get_doclink(paper_id), get_comments(paper_id)
    return create_lineage_relations(paper_id), create_lineage_explore(paper_id)


@callback(
    [Output('store_lineage_relations', 'data', allow_duplicate=True),
     Output('id_src_paper', 'children'),
     Output('id_src_paper', 'title'),
     Output('id_lineage', 'children')
     ],
    [Input('store_lineage_relations', 'data'),
     State('id_tgt_paper', 'value')],
    prevent_initial_call=True,
    suppress_callback_exceptions=True
)
def get_lineage_relations(lineage_relations, target):
    log(f'callback get_lineage_relations(): entered.')
    if lineage_relations is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    paper_id = lineage_relations.get('core', None)
    paper = state.get_paper(paper_id)
    paper_name = paper.get('paper_name') if paper else None
    paper_name_show = paper_name if paper_name is not None and len(paper_name) < 45 else (paper_name[:42] + '...')
    src_link = lineage_relations.get('src_link')
    lineage_relations_layout = generate_lineage_graph(src_link, None)
    print(f'DEBUG: get_lineage_relations(): lineage_relations_layout={lineage_relations_layout}')
    return create_lineage_relations(paper_id, target), f'{paper_id} - {paper_name_show}', f'{paper_id} - {paper_name}', lineage_relations_layout


@callback(
    [Output('id_current_paper', 'children'),
     Output('dblclick_citations', 'children'),
     Output('dblclick_references', 'children'),
     Output('id_visit_traces', 'children')
     ],
    [Input('store_lineage_explore', 'data')],
    prevent_initial_call=True,
    suppress_callback_exceptions=True
)
def update_by_lineage_explore(lineage_explore):
    log(f'callback update_by_lineage_explore(): entered.')
    if lineage_explore is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    log(f'callback update_by_lineage_explore(): lineage_explore={lineage_explore}')
    pos = lineage_explore.get('pos')
    visit_traces = lineage_explore.get('visit_traces')
    paper_id = visit_traces[pos]
    log(f'callback update_by_lineage_explore(): paper_id={paper_id}')
    table_paper_detail = gen_current_paper_detail(paper_id)
    table_citations_layout = gen_citations_or_references_table(paper_id, opt='citations',
                                                               lineage_explore=lineage_explore)
    table_references_layout = gen_citations_or_references_table(paper_id, opt='references',
                                                                lineage_explore=lineage_explore)
    visit_traces_layout = gen_visit_traces_layout(lineage_explore)
    return table_paper_detail, table_citations_layout, table_references_layout, visit_traces_layout


@callback(
    Output('table_citations', 'style_data_conditional'),
    [Input('table_citations', 'data'),
     Input('table_citations', 'page_current'),
     Input('table_citations', 'page_size')]
)
def update_table_citations_row_style(data, page_current, page_size):
    if page_current is None:
        page_current = 0
    return util.update_row_style_by_flag(data[page_current*page_size: page_current*page_size + page_size])


@callback(
    Output('table_references', 'style_data_conditional'),
    [Input('table_references', 'data'),
     Input('table_references', 'page_current'),
     Input('table_references', 'page_size')]
)
def update_table_references_row_style(data, page_current, page_size):
    if page_current is None:
        page_current = 0
    return util.update_row_style_by_flag(data[page_current*page_size: page_current*page_size + page_size])


@callback(
    Output('id_citations_link_src', 'children'),
    [Input('id-citations-slider', 'value')],
    prevent_initial_call=True
)
def update_output(value):
    # 这里的value是一个列表，包含了滑动条的两个端点值
    print(f'DEBUG: You have selected: {value}')
    return dash.no_update


@callback(Output('has_dblclick_on_citations', 'data', allow_duplicate=True),
          [Input('dblclick_references', 'event')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True
          )
def record_dblclick_citations(event):
    log(f'callback record_dblclick_citations(): entered.')
    page_x = event['pageX']
    if page_x < 600:
        log(f'callback record_dblclick_citations(): event={event}')
        return event
    return dash.no_update


@callback(Output('has_dblclick_on_references', 'data', allow_duplicate=True),
          [Input('dblclick_references', 'event')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True
          )
def record_dblclick_references(event):
    log(f'callback record_dblclick_references(): entered.')
    page_x = event['pageX']
    if page_x > 900:
        log(f'callback record_dblclick_references(): event={event}')
        return event
    return dash.no_update


@callback([Output('store_lineage_explore', 'data', allow_duplicate=True),
           Output('has_dblclick_on_references', 'data', allow_duplicate=True)],
          [Input('has_dblclick_on_references', 'data'),
           Input('store_lineage_explore', 'data'),
           Input('table_references', 'active_cell'),
           Input('table_references', 'page_current'),
           State('table_references', 'page_size'),
           State('table_references', 'data')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True
)
def on_dblclick_table_references(event, lineage_explore, active_cell, page_current, page_size, table_data):
    log(f'callback on_dblclick_table_references(): enter.')
    if event and active_cell:
        log(f'callback on_dblclick_table_references(): event = {event}')
        row = util.web_table_row(active_cell, page_current, page_size, table_data)
        paper_id = row.get('paper_id', None) if row is not None else None
        if paper_id is None:
            return dash.no_update, None
        pos = lineage_explore['pos']
        visit_traces = lineage_explore['visit_traces']
        pos += 1
        log(f'callback on_dblclick_table_references(): paper_id={paper_id}')
        if pos >= len(visit_traces):
            if paper_id != visit_traces[pos-1]:
                visit_traces.append(paper_id)
            else:
                pos -= 1
        elif paper_id != visit_traces[pos]:
            visit_traces[pos] = paper_id
            visit_traces = visit_traces[:pos + 1]
        log(f'callback on_dblclick_table_references(): pos={pos}, visit_traces={visit_traces}')
        lineage_explore['visit_traces'] = visit_traces
        lineage_explore['pos'] = pos
        log(f'callback on_dblclick_table_references(): updated lineage_explore={lineage_explore}')
        return lineage_explore, None
    return dash.no_update, None


@callback([Output('store_lineage_explore', 'data', allow_duplicate=True),
           Output('has_dblclick_on_citations', 'data', allow_duplicate=True)],
          [Input('has_dblclick_on_citations', 'data'),
           Input('store_lineage_explore', 'data'),
           Input('table_citations', 'active_cell'),
           Input('table_citations', 'page_current'),
           State('table_citations', 'page_size'),
           State('table_citations', 'data')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True
)
def on_dblclick_table_citations(event, lineage_explore, active_cell, page_current, page_size, table_data):
    log(f'callback on_dblclick_table_citations() enter.')
    if event and active_cell:
        log(f'callback on_dblclick_table_citations(): event = {event}')
        row = util.web_table_row(active_cell, page_current, page_size, table_data)
        paper_id = row.get('paper_id', None) if row is not None else None
        if paper_id is None:
            return dash.no_update, None
        pos = lineage_explore['pos']
        visit_traces = lineage_explore['visit_traces']
        log(f'callback on_dblclick_table_citations(): paper_id={paper_id}')
        pos -= 1
        if pos < 0:
            pos = 0
            if paper_id != visit_traces[0]:
                visit_traces.insert(0, paper_id)
        elif paper_id != visit_traces[pos]:
            visit_traces[pos] = paper_id
            visit_traces = visit_traces[pos:]
        log(f'callback on_dblclick_table_citations(): pos={pos}, visit_traces={visit_traces}')
        lineage_explore['visit_traces'] = visit_traces
        lineage_explore['pos'] = pos
        log(f'callback on_dblclick_table_citations(): updated lineage_explore={lineage_explore}')
        return lineage_explore, None
    return dash.no_update, None


@callback(Output('div_summary_reference', 'children', allow_duplicate=True),
          [Input('table_references', 'active_cell'),
           Input('table_references', 'page_current'),
           State('table_references', 'page_size'),
           State('table_references', 'data')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True
)
def show_reference_summary(active_cell, page_current, page_size, table_data):
    log(f'callback show_reference_summary() enter.')
    if active_cell is None:
        return dash.no_update
    row = util.web_table_row(active_cell, page_current, page_size, table_data)
    paper_id = row.get('paper_id', None) if row else None
    if paper_id is None:
        return dash.no_update
    return gen_paper_summary(paper_id, 'id_summary_reference')


@callback(Output('div_summary_citation', 'children', allow_duplicate=True),
          [Input('table_citations', 'active_cell'),
           Input('table_citations', 'page_current'),
           State('table_citations', 'page_size'),
           State('table_citations', 'data')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True
)
def show_citation_summary(active_cell, page_current, page_size, table_data):
    log(f'callback show_citation_summary() enter.')
    if active_cell is None:
        return dash.no_update
    row = util.web_table_row(active_cell, page_current, page_size, table_data)
    paper_id = row.get('paper_id', None) if row else None
    if paper_id is None:
        return dash.no_update
    return gen_paper_summary(paper_id, 'id_summary_citation')


@callback(Output('store_lineage_explore', 'data', allow_duplicate=True),
          [Input('btn_forward', 'n_clicks'),
           Input('store_lineage_explore', 'data')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True
)
def visit_forward(n_clicks, lineage_explore):
    log(f'callback visit_forward() enter.')
    if not ctx.triggered:
        return dash.no_update

    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_forward':
        visit_traces = lineage_explore['visit_traces']
        pos = lineage_explore['pos']
        pos += 1
        if pos < len(visit_traces):
            lineage_explore['pos'] = pos
            return lineage_explore
    return dash.no_update


@callback(Output('store_lineage_explore', 'data', allow_duplicate=True),
          [Input('btn_back', 'n_clicks'),
           Input('store_lineage_explore', 'data')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True
)
def visit_backward(n_clicks, lineage_explore):
    log(f'callback visit_backward() enter.')
    if not ctx.triggered:
        return dash.no_update

    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_back':
        pos = lineage_explore['pos']
        pos -= 1
        if pos >= 0:
            lineage_explore['pos'] = pos
            return lineage_explore
    return dash.no_update


@callback(Output('lineage_paper_pdf_url', 'data', allow_duplicate=True),
          [Input('btn_read_cur_paper', 'n_clicks'),
           Input('store_lineage_explore', 'data')
           ],
          prevent_initial_call=True
          )
def open_cur_paper_pdf(n_clicks, lineage_explore):
    log(f'callback open_cur_paper_pdf(): entered.')
    if not ctx.triggered:
        return dash.no_update
    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_read_cur_paper':
        if n_clicks > 0 and (lineage_explore is not None):
            visit_traces = lineage_explore.get('visit_traces', None)
            pos = lineage_explore.get('pos')
            paper_id = visit_traces[pos] if visit_traces else None
            if paper_id is not None:
                return {"url": f'/comment?paper_id={paper_id}'}
    return dash.no_update


@callback(Output('lineage_paper_pdf_url', 'data', allow_duplicate=True),
          [Input('btn_read_citation', 'n_clicks'),
           Input('table_citations', 'active_cell'),
           Input('table_citations', 'page_current'),
           State('table_citations', 'page_size'),
           State('table_citations', 'data')],
          prevent_initial_call=True
          )
def open_citation_pdf(n_clicks, active_cell, page_current, page_size, table_data):
    log(f'callback open_citation_pdf(): entered.')
    if not ctx.triggered:
        return dash.no_update
    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_read_citation':
        row = util.web_table_row(active_cell, page_current, page_size, table_data)
        paper_id = row.get('paper_id', None) if row else None
        if paper_id is not None:
            log(f'callback open_citation_pdf(): selected paper {paper_id}')
            return {"url": f'/comment?paper_id={paper_id}'}
    return dash.no_update


@callback(Output('lineage_paper_pdf_url', 'data', allow_duplicate=True),
          [Input('btn_read_reference', 'n_clicks'),
           Input('table_references', 'active_cell'),
           Input('table_references', 'page_current'),
           State('table_references', 'page_size'),
           State('table_references', 'data')],
          prevent_initial_call=True
          )
def open_reference_pdf(n_clicks, active_cell, page_current, page_size, table_data):
    log(f'callback open_reference_pdf(): entered.')
    if not ctx.triggered:
        return dash.no_update
    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_read_reference':
        row = util.web_table_row(active_cell, page_current, page_size, table_data)
        paper_id = row.get('paper_id', None) if row else None
        if paper_id is not None:
            log(f'callback open_reference_pdf(): selected paper {paper_id}')
            return {"url": f'/comment?paper_id={paper_id}'}
    return dash.no_update


clientside_callback(
    """
    function(url_data) {
        if (url_data && url_data.url) {
            window.open(url_data.url, '_blank'); // Open the URL in a new tab
        }
        return null;
    }
    """,
    Input('lineage_paper_pdf_url', 'data')  # Triggered when the store data changes
)

