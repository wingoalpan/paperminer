#!/usr/bin/env python
# coding: utf-8
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
        # dbc.NavItem(dbc.NavLink("Favorites", href="/favorite")),
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
    paper_node = html.Div([
        # paper_id
        html.Div(
            html.Label(f'{paper_id}:',
                       # className=' tooltip',
                       style={'font-weight': 'bold', 'font-size': 10,
                              'max-height': 25, 'display': 'inline-block'}
                       ),
            className='div-ellipsis',
            title=paper_id,
            style={'margin-bottom': '2px'}
        ),
        # paper_name
        html.Div(
            html.Label(f'{paper_name}', style={'max-height': 60}),
            className='div-ellipsis'
        ),
    ], className='div-border ml-5 mr-5 mt-2 mb-2',
        style={'width': 110, 'height': 80, 'background-color': 'black'})
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
                         className='mt-2',
                         style={'background-color': 'gray'}, ),
                html.Div(generate_paper_nodes(src_link_show),
                         className='div-flex-left mt-2',
                         style={'background-color': 'blue'},
                         id='id_citations_link_src'),
                html.Div([generate_paper_node(connection)],
                         className='mt-2',
                         style={'background-color': 'gray'}),
                html.Div(generate_paper_nodes(target_link_show),
                         className='div-flex-left mt-2',
                         style={'background-color': 'blue'},
                         id='id_citations_link_target'),
                html.Div([generate_paper_node(target_show)],
                         className='mt-2',
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
        ], className='mt-2', style=lineage_link_style
        ),
    ], className='div-flex-left',
        style=lineage_graph_style)
    return lineage_graph


def gen_citations_or_references_table(paper_id, opt='citations', flag_refs=None):
    lineage_graph = state.lineage_graph
    relations = lineage_graph.get(paper_id, {}).get(opt, None) if (paper_id is not None) else None
    table_config = {'table_width': 500,
                    'table_height': 300,
                    'column_settings': {
                        'paper_id': {'width': '20%'},
                        'paper_name': {'width': '55%', 'tip': True},
                        'ref_no': {'width': '15%'},
                        'flag': {'width': '10%'}
                    }}
    if relations:
        related_papers = [(lineage_graph.get(relation[0], {}).get('paper', None), relation[1]) for relation in relations]
        data = [[paper['paper_id'], paper['paper_name'], ref_no, '☆' if paper['paper_id'] in flag_refs else None]
                for paper, ref_no in related_papers if paper is not None]
        df_table = pd.DataFrame(data, columns=['paper_id', 'paper_name', 'ref_no', 'flag'])
    else:
        df_table = pd.DataFrame([], columns=['paper_id', 'paper_name', 'ref_no', 'flag'])
    table_layout = EventListener(
        id=f'dblclick_{opt}',
        events=[{'event': 'dblclick', 'props': ['srcElement.className', 'srcElement.id', 'srcElement.innerText']}],
        children=util.create_table_layout(f'table_{opt}', df_table, table_config, max_rows=50)
    )
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
    columns_info = {
        'paper_id': {'id': 'paper_paper_id', 'name': 'Paper ID', 'height': 25},
        'publish_date': {'id': 'paper_publish_date', 'name': 'Publish Date', 'height': 25},
        'paper_name': {'id': 'paper_paper_name', 'name': 'Paper Name', 'height': 50,
                       'style': {'font-weight': 'bold', 'font-size': 13}},
        'authors': {'id': 'paper_authors', 'name': 'Authors', 'height': 120},
        'weblink': {'id': 'paper_weblink', 'name': 'Web Site', 'height': 42}
    }
    return util.detail(paper, columns_info, 100, 450, 'id_current_paper_detail')


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
    dcc.Store(id='store_lineage_paper_id', data=None),
    # core, target, src_link, target_link
    dcc.Store(id='store_lineage_relations', data=None),
    # core, visit_traces, cur_pos
    dcc.Store(id='store_lineage_explore', data=None),

    # 论文谱系查询
    dbc.Row(dbc.Col(navbar, width=15),
            class_name="d-flex justify-content-center mt-2 mb-2"),
    html.Div([
        # 源论文 和 目标论文选择
        html.Div([
            html.Div([
                html.Div(html.Label('Source Paper:'), className='mr-5', style={'width': 90}),
                html.Div(html.Label(state.current_paper, id='id_src_paper'), className='ml-5')
            ], className='div-flex-left', style={'width': '40%', 'height': 25}),
            html.Div([
                html.Div(html.Label('Target Paper:'), className='mr-10'),
                html.Div(html.Label('', id='id_tgt_paper'), className='ml-10',
                         style={'width': 150}),
                html.Div(dcc.Input('Attention is all you need', id='id_tgt_match_pat',
                                   style={'width':150, 'height': 25, 'margin-left': 10})),
            ], className='div-flex-left mt-2 mb-2', style={'width': '40%', 'height': 35}),
            html.Div([
                html.Div(html.Button('选择', id='btn_select_tgt', style={'height': 25, 'margin-left': 10}))
            ]),
        ], className='div-flex-left mb-2',
            style={
                  'width': '1200px', 'height': 35}
        ),
        # 论文关系链
        html.Div(id='id_lineage'),
    ], className='div-border mb-10'),
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
    ], className='div-flex-left', style={'width': '100%', 'height': 25}),
    # 论文关系区
    html.Div([
        html.Div([
            html.Div(gen_citations_or_references_table(None, opt='citations'),
                     id='id_paper_citations', className='div1 div-border ml-5 mr-20',
                     style={'display': 'inline-block', 'width': '40%', 'height': 350}
            ),
            # 当前论文概要信息
            html.Div([
                html.Div([], id='id_current_paper',
                         className='div-flex-left div-border mb-2',
                         style={'height': 315, 'margin-bottom': '1px'}),
                # 论文访问 向前/向后 按钮
                html.Div([
                    html.Button('Back', id='btn_back',
                                className='centered-button mr-10',
                                style={'width': 80, 'height': 25}),
                    html.Button('Forward', id='btn_forward',
                                className='centered-button ml-10',
                                style={'width': 80, 'height': 25}),
                ],
                    className='div-flex-center div-border',
                    style={'height': 25, 'margin-top': '1px'}),
            ], className='div-border ml-10 mr-10',
                style={'width': '30%', 'height': 350}),
            html.Div(gen_citations_or_references_table(None, opt='references'),
                     id='id_paper_refs', className='div3 div-border ml-20 mr-5',
                     style={'display': 'inline-block', 'width': '40%', 'height': 350})
        ], className='div-flex-left', style={'width': '100%', 'height': 360}),
    ], className='div-border mb-10'),
    html.Div([], id='id_paper_detail',
             className='div-border',
             style={'width': '100%', 'height': 150}),
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
        return dash.no_update, dash.no_update, dash.no_update
    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_close_modal_select_target':
        if page_current is None:
            page_current = 0
        if active_cell is None:
            log('callback on_selected_target(): no cell selected')
            raise PreventUpdate
        selected_index = active_cell['row'] + page_current * page_size
        if len(table_data) > 0:
            row = table_data[selected_index]
            target = row['paper_id']
            log(f'callback on_selected_target(): selected target={target}')
            src = lineage_relations.get('core')
            return False, target, create_lineage_relations(src, target)
    return dash.no_update, dash.no_update, dash.no_update


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
        return dash.no_update, dash.no_update, dash.no_update
    paper_id = lineage_relations.get('core', None)
    src_link = lineage_relations.get('src_link')
    lineage_relations_layout = generate_lineage_graph(src_link, None)
    print(f'DEBUG: get_lineage_relations(): lineage_relations_layout={lineage_relations_layout}')
    return create_lineage_relations(paper_id, target), paper_id, lineage_relations_layout


@callback(
    [Output('id_current_paper', 'children'),
     Output('id_paper_citations', 'children'),
     Output('id_paper_refs', 'children'),
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
    pos = lineage_explore.get('pos')
    visit_traces = lineage_explore.get('visit_traces')
    paper_id = visit_traces[pos]
    log(f'callback update_by_lineage_explore(): paper_id={paper_id}')
    table_paper_detail = gen_current_paper_detail(paper_id)
    table_citations_layout = gen_citations_or_references_table(paper_id, opt='citations', flag_refs=visit_traces)
    table_references_layout = gen_citations_or_references_table(paper_id, opt='references', flag_refs=visit_traces)
    visit_traces = gen_visit_traces_layout(lineage_explore)
    return table_paper_detail, table_citations_layout, table_references_layout, visit_traces


@callback(
    Output('table_citations', 'style_data_conditional'),
    [Input('table_citations', 'data')]
)
def update_table_citations_row_style(data):
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
    Output('table_references', 'style_data_conditional'),
    [Input('table_references', 'data')]
)
def update_table_references_row_style(data):
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
    Output('id_citations_link_src', 'children'),
    [Input('id-citations-slider', 'value')],
    prevent_initial_call=True
)
def update_output(value):
    # 这里的value是一个列表，包含了滑动条的两个端点值
    print(f'DEBUG: You have selected: {value}')
    return dash.no_update


@callback(Output('store_lineage_explore', 'data', allow_duplicate=True),
          [Input('dblclick_references', 'event'),
           Input('store_lineage_explore', 'data'),
           Input('table_references', 'active_cell'),
           Input('table_references', 'page_current'),
           State('table_references', 'page_size'),
           State('table_references', 'data')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True
)
def on_dblclick_table_references(event, lineage_explore, active_cell, page_current, page_size, table_data):
    log(f'callback on_dblclick_table_references() enter.')
    if event and active_cell:
        if page_current is None:
            page_current = 0
        selected_index = active_cell['row'] + page_current * page_size
        data_row = table_data[selected_index]
        paper_id = data_row['paper_id']
        log(f'callback on_dblclick_table_references(): selected paper_id = {paper_id}')
        pos = lineage_explore['pos']
        visit_traces = lineage_explore['visit_traces']
        pos += 1
        if pos >= len(visit_traces):
            visit_traces.append(paper_id)
        else:
            last_visited_id = visit_traces[pos]
            if paper_id != last_visited_id:
                visit_traces[pos] = paper_id
                visit_traces = visit_traces[:pos + 1]
        lineage_explore['visit_traces'] = visit_traces
        lineage_explore['pos'] = pos
        return lineage_explore
    else:
        raise PreventUpdate


@callback(Output('store_lineage_explore', 'data', allow_duplicate=True),
          [Input('dblclick_citations', 'event'),
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
        if page_current is None:
            page_current = 0
        print(f'DEBUG: on_dblclick_table_citations(): event[srcElement.className] = {event["srcElement.className"]}')
        selected_index = active_cell['row'] + page_current * page_size
        data_row = table_data[selected_index]
        paper_id = data_row['paper_id']
        log(f'callback on_dblclick_table_citations(): selected paper_id = {paper_id}')
        pos = lineage_explore['pos']
        visit_traces = lineage_explore['visit_traces']
        pos -= 1
        if pos < 0:
            pos = 0
            visit_traces.insert(0, paper_id)
        else:
            last_visited_id = visit_traces[pos]
            if paper_id != last_visited_id:
                visit_traces[pos] = paper_id
                visit_traces = visit_traces[pos:]
        lineage_explore['visit_traces'] = visit_traces
        lineage_explore['pos'] = pos
        return lineage_explore
    else:
        raise PreventUpdate


@callback(Output('store_lineage_explore', 'data', allow_duplicate=True),
          [Input('btn_forward', 'n_clicks'),
           Input('store_lineage_explore', 'data')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True
)
def visit_forward(n_clicks, lineage_explore):
    log(f'callback visit_backward() enter.')
    if not ctx.triggered:
        return dash.no_update

    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_forward':
        visit_traces = lineage_explore['visit_traces']
        pos = lineage_explore['pos']
        pos += 1
        if pos >= len(visit_traces):
            return dash.no_update
        else:
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
        visit_traces = lineage_explore['visit_traces']
        pos = lineage_explore['pos']
        pos -= 1
        if pos < 0:
            return dash.no_update
        else:
            lineage_explore['pos'] = pos
            return lineage_explore
    return dash.no_update


