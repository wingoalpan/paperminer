#!/usr/bin/env python
# coding: utf-8
import os
import dash
import dash_bootstrap_components as dbc
from flask import Flask
from flask import send_from_directory

import wingoal_utils.common as cm
from wingoal_utils.common import (set_log_file, log)
import webutil as util
import papersearch as ps

set_log_file(os.path.split(__file__)[-1], timestamp=True)

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.4/dbc.min.css"
bWLwgP = "https://codepen.io/chriddyp/pen/bWLwgP.css"
external_stylesheets = [bWLwgP, dbc.themes.BOOTSTRAP, dbc_css, dbc.themes.MINTY] #, dbc.themes.SUPERHERO]
external_scripts = ['https://cdn.quilljs.com/1.3.6/quill.js'] #, 'assets/custom.js']

navbar = dbc.NavbarSimple(
    [
        dbc.NavItem(dbc.NavLink("Home", href="/")),
        dbc.NavItem(dbc.NavLink("Favorites", href="/favorite")),
        dbc.NavItem(dbc.NavLink("Comment", href="/comment")),
    ],
    brand="Wingoal Pan",
    brand_href="#",
    color="primary",
    dark=True,
    style={'height': '40px', 'margin-bottome': '5px'}
)


server = Flask(__name__)
app_paper_browse = dash.Dash(__name__, server=server,
                             title='Papers Viewer',
                             use_pages=True,
                             external_stylesheets=external_stylesheets,
                             external_scripts=external_scripts)

state = util.get_state()

app_paper_browse.layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                    dash.page_container,
                    width=16,
                    style={"height": "auto"}
                    ),
            class_name="mh-10 d-flex justify-content-center"
        ),
    ],
    fluid=True,
)


@app_paper_browse.server.route('/pdf/<paper_id>')
def send_pdf(paper_id):
    log(f'callback server.send_pdf(): enter.')
    papers_pdf_dir = '../papers'
    paper = state.get_paper(paper_id)
    if paper:
        paper_pdf = paper.get('paper_pdf', None)
        file_path = os.path.join(papers_pdf_dir, paper_pdf)
        if os.path.exists(file_path):
            return send_from_directory(papers_pdf_dir, paper_pdf)
        elif ps.download_paper(paper, papers_pdf_dir):
            return send_from_directory(papers_pdf_dir, paper_pdf)
        log(f'server.send_pdf(): Failed to download pdf of paper (paper_id={paper_id})!')
    else:
        log(f'server.send_pdf(): Invalid paper (paper_id={paper_id}) requested. ')

    return None


if __name__ == '__main__':
    log(f'starting app_paper_browse server ...')
    app_paper_browse.run_server(debug=True)
