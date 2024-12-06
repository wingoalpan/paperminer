#!/usr/bin/env python
# coding: utf-8
import os
import dash
import dash_bootstrap_components as dbc
from flask import Flask
from flask import send_from_directory

from wingoal_utils.common import (set_log_file, log)
import webutil as util
import papersearch as ps

set_log_file(os.path.split(__file__)[-1], timestamp=True)

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.4/dbc.min.css"
bWLwgP = "https://codepen.io/chriddyp/pen/bWLwgP.css"
external_stylesheets = [bWLwgP, dbc.themes.BOOTSTRAP, dbc_css, dbc.themes.MINTY]
external_scripts = ['https://cdn.quilljs.com/1.3.6/quill.js']

server = Flask(__name__)
app_paper_browse = dash.Dash(__name__, server=server,
                             title='Papers Viewer',
                             use_pages=True,
                             external_stylesheets=external_stylesheets,
                             external_scripts=external_scripts,
                             suppress_callback_exceptions=True)

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
    # 若正式部署，则应删除这段启动代码，而改用命令行
    #  waitress-serve --host 0.0.0.0 --port 8050 webapp:server
    log(f'starting app_paper_browse server ...')
    app_paper_browse.run_server(debug=True)
