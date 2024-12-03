#!/usr/bin/env python
# coding: utf-8
import dash
from dash import dcc
from dash import html
from dash import Input, Output, callback, State, ctx, clientside_callback
import dash_bootstrap_components as dbc
import dash_quill as quill

import webutil as util

from wingoal_utils.common import log

dash.register_page(__name__, path='/comment')

state = util.get_state()

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
    style={'height': 40, 'margin-bottome': '5px'}
)


def get_doclink(paper_id):
    if paper_id is None:
        return ""
    paper = state.get_paper(paper_id)
    doclink = paper.get('doclink', '') if paper else ""
    return doclink


def get_comments(paper_id):
    if paper_id is None:
        return ''
    return state.get_comments(paper_id)


layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='store_paper_id', data=None),
    html.Link(href="https://cdn.staticfile.org/quill/1.3.6/quill.snow.css", rel="stylesheet"),
    html.Script(
        src="https://cdn.staticfile.org/quill/1.3.6/quill.js"
    ),
    html.Div([
            html.Iframe(
                id='id_doclink',
                src='',
                style={
                    'width': '1200px',
                    'height': 720,
                    'margin-left': '10px'
                }
            )
    ], style={'width': '1200px', 'height': 720}
    ),
    html.Div([
        html.Div(navbar, style={'margin-bottom': 5}),
        html.Div([
            quill.Quill(
                id='comments_editor',
                value='my-value',
                maxLength=512,
                modules={'toolbar': True, 'clipboard': {'matchVisual': False}},
            )
        ], style={'height': 640}
        ),
        html.Div([
            html.Button('保存',
                        id='btn_save_comments', n_clicks=0,
                        style={'font-size': 12, 'height': 25, 'lineHeight': 1,
                               'margin-left': 1
                               }
                        ),
        ], style={'display': 'flex', 'justify-content': 'center'}
        ),
    ], style={'margin-left': '15px', 'width': '100%'})
],
    # class_name="d-flex justify-flex-start",
    style={'display': 'flex', 'justify-content': 'flex_start', 'width': '100%'}
)


@callback(
    [Output('id_doclink', 'src'),
     Output('comments_editor', 'value'),
     Output('store_paper_id', 'data')
     ],
    [Input('url', 'pathname'),
     Input('url', 'search')],
    [State('url', 'href')],
    prevent_initial_call=True,
    suppress_callback_exceptions=True
)
def get_doclink_from_url(pathname, search, href):
    log(f'callback get_doclink_from_url(): entered.')
    # 提取查询参数
    if search:
        query = dict([param.split('=') for param in search[1:].split('&')])
        paper_id = query.get('paper_id', None)
    else:
        paper_id = state.current_paper
    log(f'callback get_doclink_from_url(): paper_id={paper_id}')
    # return get_doclink(paper_id), get_comments(paper_id)
    return f'/pdf/{paper_id}', get_comments(paper_id), paper_id


@callback([Input('btn_save_comments', 'n_clicks'),
           Input('comments_editor', 'value'),
           Input('store_paper_id', 'data')],
          prevent_initial_call=True,
          suppress_callback_exceptions=True)
def save_comments(n_clicks, value, paper_id):
    log(f'callback save_comments(): entered.')
    if not ctx.triggered:
        return

    if ctx.triggered[0]['prop_id'].split('.')[0] == 'btn_save_comments':
        login = state.login
        log(f'callback save_comments(): Saving comments: paper_id={paper_id}, login={login}')
        state.add_comments(login, paper_id, value)
    return
