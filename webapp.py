#!/usr/bin/env python
# coding: utf-8
import os
import dash
import pandas as pd
from dash import dcc
from dash import html
from dash import dash_table
from dash import Input, Output, callback, State, ctx, clientside_callback
import dash_bootstrap_components as dbc
import paperdb as db

import webutil as util

import wingoal_utils.common as cm
from wingoal_utils.common import (set_log_file, log)

set_log_file(os.path.split(__file__)[-1], timestamp=True)

external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css", dbc.themes.BOOTSTRAP] #, dbc.themes.SUPERHERO]

print(f'DEBUG: loading webapp.py ...')
app_paper_browse = dash.Dash(__name__, use_pages=True,
                             external_stylesheets=external_stylesheets, title='Papers Viewer')

print(f'DEBUG: constructing start page ...')
app_paper_browse.layout = html.Div(
    children=[
        html.Div(style={'height': 20}),
        html.Div([html.Div(html.Label("输入搜索的论文标题："),
                           className='div1'),
                  html.Div(dcc.Input(id='paper_title_searching', value='attention is all you need', type='search'),
                           className='div2'),
                  html.Div(dcc.Dropdown(['Local', 'Google'], '',
                                        placeholder="select site",
                                        id='search_site',
                                        style={'font-size': 13, 'width': 110, 'height': 25, 'lineHeight': 1,
                                               'margin-left': -2
                                               }
                                        ),
                           className='div2',
                           style={'vertical-align': 'top'}),
                  html.Div(html.Button('搜索',
                                       id='btn_search', n_clicks=0,
                                       style={'height': 35, 'lineHeight': 1,
                                              'margin-left': -2
                                              }
                                       ),
                           className='div3')
                  ],
                 style={'display': 'inline-block', 'margin-bottom': '15px'}),
        dash.page_container
    ]
)


@app_paper_browse.callback(Output('div_papers', 'children'),
                           [Input('btn_search', 'n_clicks'),
                            State('paper_title_searching', 'value')
                            ], prevent_initial_call=True
                           )
def search_paper(n_clicks, title_for_searching):
    print(f'n_clicks={n_clicks}, searching title: {title_for_searching}')
    if title_for_searching is None:
        return dash.no_update
    print(f'searching title: {title_for_searching}')
    _rows, _columns = db.query_rows(f'SELECT paper_id, paper_name, publish_date, authors ' +
                                    f'FROM papers WHERE paper_name like "%{title_for_searching}%"')
    _df_papers = pd.DataFrame(_rows, columns=_columns)
    return util.generate_table('papers', _df_papers, max_rows=50)


if __name__ == '__main__':
    print(f'starting app_paper_browse server ...')
    app_paper_browse.run_server(debug=True)
