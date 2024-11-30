
import os
import sys
import argparse
from datetime import datetime
import time
import pandas as pd
import json as js
import shutil
import arxiv
from googlesearch import search
import re

import wingoal_utils.common as cm
from wingoal_utils.common import (
    set_log_file,
    log,
    save_json,
    start_timer,
    time_elapse,
    time_str
)
sys.path.append('..')
import pdfpaper as pp
import paperef
import papersearch as ps
import paperdb as db
import schedule

set_log_file(os.path.split(__file__)[-1], timestamp=True)

db.set_db_name('../papers.db')

pdf_paths = [
        '..\\papers\\2307.08702v1(Diffusion Models Beat GANs on Image Classification).pdf',
        '..\\papers\\2112.10752v2(High-Resolution Image Synthesis with Latent Diffusion Models).pdf',
        # 含页眉，无编号，References页中开始
        '..\\papers\\2210.17323v2（GPTQ--ACCURATE POST-TRAINING QUANTIZATION FOR GENERATIVE PRE-TRAINED TRANSFORMERS）.pdf',
        # 含页眉，无编号，分栏
        '..\\papers\\2102.09672v1(Improved Denoising Diffusion Probabilistic Models).pdf',
        # 含页眉，References右侧，部分分栏，无编号
        '..\\papers\\2306.00978v4(AWQ--ACTIVATION-AWARE WEIGHT QUANTIZATION FOR LLM Compression and Acceleration)-saveas.pdf',
        # 非数字编号，行距不同
        '..\\papers\\2005.14165v4(GPT-3--Language Models are Few-Shot Learners).pdf',
        # 含页眉，无编号，分栏，References右侧页中开始
        '..\\papers\\1503.03585v8(Deep Unsupervised Learning using Nonequilibrium Thermodynamics).pdf',
        # 无编号, References页中开始
        '..\\papers\\2106.09685v2(LORA--LOW-RANK ADAPTATION OF LARGE LANGUAGE MODELS).pdf'
    ]


def verify(src_file_name, baseline_file_name, verify_result_file_name,
           verify_result_template = './paper_references_verify-template.xlsx'):
    pd_src = pd.read_excel(src_file_name)
    pd_baseline = pd.read_excel(baseline_file_name)
    pd_verify_result = pd.DataFrame()
    pd_baseline.index = pd_baseline['paper'] + ':' + pd_baseline['ref_no'].apply(lambda x: str(x))
    pd_src.index = pd_src['paper'] + ':' + pd_src['ref_no'].apply(lambda x: str(x))
    baseline = pd_baseline.to_dict('index')

    new_refs = 0
    text_incorrect = 0
    title_incorrect = 0
    authors_incorrect = 0
    ref_id_incorrect = 0
    for key, row in pd_src.iterrows():
        diffs = []
        if key not in baseline.keys():
            new_refs += 1
            row['verified'] = 'NEW REFERENCE'
            pd_verify_result._append(row, ignore_index=True)
            continue
        if row['ref_text'] != baseline[key]['ref_text']:
            text_incorrect += 1
            diffs.append('TEXT:\n   ' + baseline[key]['ref_text'] + '\n-> '+ row['ref_text'])
        if row['title'] != baseline[key]['title']:
            title_incorrect += 1
            diffs.append('TITLE:\n   ' + (str(baseline[key]['title']) if baseline[key]['title'] else '')
                             + '\n-> ' + (str(row['title']) if row['title'] else ''))
        if row['authors'] != baseline[key]['authors']:
            authors_incorrect += 1
            diffs.append('AUTHORS:\n   ' + (str(baseline[key]['authors']) if baseline[key]['authors'] else '')
                               + '\n-> ' + (str(row['authors']) if row['authors'] else ''))
        if (not pd.isna(row['ref_id']) or not pd.isna(baseline[key]['ref_id'])) and row['ref_id'] != baseline[key]['ref_id']:
            ref_id_incorrect += 1
            diffs.append('REFID:\n' + (str(baseline[key]['ref_id']) if baseline[key]['ref_id'] else '') + ' -> '
                                    + (str(row['ref_id']) if row['ref_id'] else ''))
        if diffs:
            row['verified'] = '\n'.join(diffs)
            pd_verify_result = pd_verify_result._append(row, ignore_index=True)
        else:
            row['verified'] = 'OK'
            pd_verify_result = pd_verify_result._append(row, ignore_index=True)

    miss_refs = len(pd_baseline) - (len(pd_src) - new_refs)
    verify_sum = {'new_refs': new_refs, 'miss_refs': miss_refs,
                  'text_incorrect': text_incorrect, 'title_incorrect': title_incorrect,
                  'authors_incorrect': authors_incorrect, 'ref_id_incorrect': ref_id_incorrect}
    print(js.dumps(verify_sum, indent=2))

    shutil.copyfile(verify_result_template, verify_result_file_name)
    with pd.ExcelWriter(verify_result_file_name, engine="openpyxl", mode='a', if_sheet_exists='overlay') as writer:
        pd_verify_result.to_excel(writer, index=False)
        writer._save()


def repair():
    baseline_file_name = './paper_references_baseline.xlsx'
    pd_baseline = pd.read_excel(baseline_file_name)
    pd_baseline['title'] = pd_baseline.title.apply(lambda x: x[:-1] if not pd.isna(x) and x.endswith('.') else x)
    with pd.ExcelWriter(baseline_file_name, engine="openpyxl", mode='a', if_sheet_exists='overlay') as writer:
        pd_baseline.to_excel(writer, index=False)
        writer._save()


def names_sum():
    baseline_file_name = './paper_references_baseline.xlsx'
    pd_baseline = pd.read_excel(baseline_file_name)
    all_authors = {}
    for index, row in pd_baseline.iterrows():
        if pd.isna(row['authors']):
            continue
        authors_text = row['authors'].replace("'", '"')
        print(f'index = {index}, authors = {authors_text}')
        authors = js.loads(authors_text)
        for author in authors:
            if not author in all_authors.keys():
                all_authors[author] = 1
            else:
                all_authors[author] = all_authors[author] + 1
    print(js.dumps(all_authors, indent=2))
    save_json(all_authors, './all_authors.json')


def import_refs():
    pd_refs = pd.read_excel('./paper_references_baseline.xlsx')
    rows = pd_refs.to_dict('records')
    papers_list = db.table_rows_dict('papers')
    papers = dict()
    for paper in papers_list:
        paper_id = paper['paper_id']
        papers[paper_id] = paper

    for row in rows:
        paper_name = row['paper_name']
        m = re.findall(r'(\d{4}.\d{4,5})v\d', paper_name)
        if m:
            arxiv_id = m[0]
            paper_id = f'arXiv_{arxiv_id}'
            row['paper_id'] = paper_id
            row['paper_name'] = papers[paper_id].get('paper_name')
        else:
            print(f'Invalid paper_name: {paper_name}')
    db.import_data('refs', rows)


def update_refs():
    rows = db.table_rows_dict('refs')
    for row in rows:
        ref_id = row['ref_id']
        if not ref_id:
            continue
        m = re.findall(r'\[arxiv\](\d{4}.\d{4,5})', ref_id)
        if m:
            arxiv_id = m[0]
            row['ref_id'] = 'arXiv_' + arxiv_id
            row['update_at'] = time_str()
            db.update('refs', [row], 'id')


def export_upgrade_data():
    # paper_id	paper_name	ref_no	ref_text	ref_authors	ref_id	ref_title	addition	verified_title	create_at	verify_at	update_at	status
    db.set_db_name('../papers.db')
    refs = db.table_rows_dict('refs')
    gs_papers_list = db.table_rows_dict('papers')
    pd_papers = pd.read_excel('../papers.xlsx', sheet_name='papers')
    src_papers_list = pd_papers.to_dict('records')
    for paper in src_papers_list:
        paper['create_at'] = '2024-11-10 09:00:00'
        paper['parseref_at'] = '2024-11-13 09:00:00'
    papers = cm.diclist2dic(src_papers_list + gs_papers_list, 'paper_id')

    # 1. 源头paper导出
    ex_papers = src_papers_list
    # 2. arXiv ref paper导出
    ex_papers = src_papers_list
    for ref in refs:
        ref_id = ref['ref_id']
        if not ref_id or ref_id in papers.keys():
            continue
        paper = dict()
        paper['paper_id'] = ref['ref_id']
        paper['paper_name'] = ref['verified_title']
        paper['authors'] = ref['ref_authors']
        paper['create_at'] = ref['verify_at']
        ex_papers.append(paper)
        papers[ref_id] = paper
    # 3. Google Scholar ref paper导出
    for paper in gs_papers_list:
        paper['create_at'] = paper['update_at']
        paper['status'] = 'verified'
        ex_papers.append(paper)
    ex_papers.sort(key=lambda x: x['create_at'], reverse=False)
    columns = ['paper_id', 'paper_name', 'authors', 'abstract', 'arxiv_id_v', 'weblink',
               'paper_pdf', 'citations', 'publisher', 'pub_year',
               'download_at', 'parseref_at', 'create_at', 'update_at', 'status']
    pd_papers = pd.DataFrame(ex_papers, columns=columns)
    pd_papers.to_excel('../import/import_papers.xlsx')


def upgrade():
    db.set_db_name('../papers.db')
    db.init_db('../papers.sql')
    db.import_excel('papers', '../import/import_papers.xlsx')
    db.import_excel('refs', '../import/import_refs.xlsx')


def complete_paper_data():
    db.set_db_name('../papers.db')
    schedule.complete_paper_data(start=426)


def extract_papers_references():
    db.set_db_name('../papers.db')
    schedule.extract_papers_references(15)


def update_arxiv_doclink():
    rows_dict = db.table_rows_dict('papers')
    updated_count = 0
    for no, row in enumerate(rows_dict):
        if not row['paper_id'].startswith('arXiv_') or row['doclink']:
            continue
        print(f'Verifying doclink of paper {row["paper_id"]}  [{no+1}]...')
        status = ps.get_arxiv_paper_by_id(row['paper_id'])
        if status.get('doclink', None):
            row['doclink'] = status['doclink']
            db.update('papers', row, 'paper_id', columns=['doclink'])
            updated_count += 1
        elif status.get('fail_network', None):
            print(f'The network request was rejected, Please retry hours later!')
            break
    print(f'Totally {updated_count} papers updated!')


def update_paper_pdf():
    rows_dict = db.table_rows_dict('papers')
    update_rows = []
    for row in rows_dict:
        paper_name = row['paper_name']
        paper_id = row['paper_id']
        if paper_id.startswith('GS_'):
            paper_id = paper_id[3:]
            title_fn = re.sub(r'[\\\/:*?"<>|]', '-', paper_name)
            paper_pdf_file = f'{paper_id}({title_fn}).pdf'
            if row['paper_pdf'] != paper_pdf_file:
                row['paper_pdf'] = paper_pdf_file
                update_rows.append(row)
    db.batch_update('papers', update_rows, 'paper_id', update_columns=['paper_pdf'])


def test_open_pdf():
    import webbrowser
    chrome_path='C:\\Users\\pypy2\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe'
    print(f'open_paper_pdf(): ')
    chrome = webbrowser.get(chrome_path)
    print(f'open_paper_pdf(): {chrome}')
    chrome.open_new_tab('https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/HintonDengYuEtAl-SPM2012.pdf')
    # return dash.no_update


def _get_citations_of_arxiv_paper(paper_id, title):
    status = {'source': 'GoogleSearch'}
    pat_arxiv_id_url = r'(http[s]*[\:]//arxiv.org/(abs|pdf)[/](?P<id>(\d{4}\.\d{4,5})|([a-z]+/\d{5,}))$)'
    pat_arxiv_id_title = r'(^\[(?P<id>\d{4}\.\d{4,5})\]\s)'
    pat_desc_head = r'(^by\s(?P<publisher>([A-Z][\w]*)(\s[A-Z][\w]*)*)[\s]?\·[\s]?((?P<year>\d{4})?[\s]?\·[\s]?)*Cited by[\s]?(?P<citations>[\d]+)\s—)'
    candidates = {}   # save the title similarity {'arxiv_id': 0.9}
    searched_results = []
    try:
        results = search(f"arxiv: {title}",
                         advanced=True, sleep_interval=3, num_results=20)
        for result in results:
            searched_results.append(result)
    except Exception as e:
        log(f'Exception caught in _get_citations_of_arxiv_paper(): {e}')
        status['fail_network'] = True
        return status
    if len(searched_results) == 0:
        status['fail_network'] = True
        return status

    # 提取 arXiv 相关结果
    for result in searched_results:
        m = re.match(pat_arxiv_id_url, result.url.strip())
        if not m:
            continue
        arxiv_id = m.group('id')
        _is_partial_title = result.title.endswith('...')
        _searched_title = result.title[:-4] if _is_partial_title else result.title
        m = re.match(pat_arxiv_id_title, _searched_title)
        if m:
            id_prefix = m.group(0)
            _searched_title = _searched_title[len(id_prefix):]
        _similarity = ps.text_similarity(title.lower(), _searched_title.lower())
        _additions = dict()
        _additions['is_partial_title'] = _is_partial_title
        # example of result.description: 'by M Wenzel · 2022 · Cited by 11 — This chapter gives a basic introduction into the motivation for Generative Adversarial Networks (GANs) and traces the path of their success.'
        m = re.match(pat_desc_head, result.description)
        if m:
            _additions['publisher'] = m.group('publisher')
            _additions['publish_date'] = m.group('year') if m.group('year') else ''
            _additions['citations'] = m.group('citations')
        # title相似度高的结果优先
        if arxiv_id not in candidates.keys() or _similarity > candidates[arxiv_id][1]:
            candidates[arxiv_id] = [_searched_title, _similarity, _additions]
    if not candidates:
        # title_fn = re.sub(r'[\\\/:*?"<>|]', '-', title)
        # cache_html_file = f'logs/{title_fn}.html'
        # with open(cache_html_file, 'w', encoding='utf-8') as f:
        #     f.write(soup.prettify())
        status['fail_googl_search'] = True
        return status
    sorted_candidates = sorted(candidates.items(), key=lambda x: x[1][1], reverse=True)
    for candidate in sorted_candidates:
        best_arxiv_id, (searched_title, _, additions) = candidate
        paper_arxiv_id = paper_id[len('arXiv_'):]
        if (best_arxiv_id == paper_arxiv_id) and additions.get('citations', None):
            status['citations'] = additions['citations']
            return status
    return status


def update_arxiv_citations():
    rows_dict = db.table_rows_dict('papers')
    updated_count = 0
    for no, row in enumerate(rows_dict):
        if not row['paper_id'].startswith('arXiv_') or row['citations']:
            continue
        print(f'Verifying citations of paper {row["paper_id"]}  [{no+1}]...')
        status = _get_citations_of_arxiv_paper(row['paper_id'], row['paper_name'])
        if status.get('citations', None):
            row['citations'] = int(status['citations'])
            db.update('papers', row, 'paper_id', columns=['citations'])
            print(f'citations={row["citations"]}')
            updated_count += 1
        elif status.get('fail_network', None):
            print(f'The network request was rejected, Please retry hours later!')
            break
    print(f'Totally {updated_count} papers updated!')


def update_publish_date():
    rows_dict = db.table_rows_dict('papers')
    updated_count = 0
    for no, row in enumerate(rows_dict):
        publish_date = row['publish_date']
        if not publish_date:
            continue
        if publish_date[0] == 'Y':
            row['publish_date'] = publish_date[1:]+'Y'
            db.update('papers', row, 'paper_id', columns=['publish_date'])
            updated_count += 1
    print(f'Totally {updated_count} papers updated!')


def test_download_pdf():
    import requests
    import papersearch as ps
    doclink = 'https://ojs.aaai.org/index.php/AAAI-SS/article/download/31243/33403'
    content = ps.download_content(doclink)
    with open('../output/test_download_pdf.pdf', 'wb') as pdf:
        pdf.write(content)
    print(content)


def update_download_at():
    papers_pdf_dir = '../../papers'
    rows_dict = db.table_rows_dict('papers')
    updated_count = 0
    for no, row in enumerate(rows_dict):
        paper_pdf = row.get('paper_pdf', None)
        file_path = os.path.join(papers_pdf_dir, paper_pdf)
        if os.path.exists(file_path) and not row.get('download_at', None):
            create_time = datetime.fromtimestamp(os.path.getctime(file_path))
            create_at = datetime.strftime(create_time, '%Y-%m-%d %H:%M:%S.%f')
            row['download_at'] = create_at[:-3]
            print(js.dumps(row, indent=2))
            db.update('papers', row, 'paper_id', columns=['download_at'])
            updated_count += 1
    print(f'Totally {updated_count} papers updated!')


def main():
    print('')
    update_download_at()


def table_rows_conditions():
    rows = db.table_conditions('refs', {'paper_id': 'arXiv_1605.09782', 'ref_no': 35})
    print(js.dumps(rows, indent=2))


def query_sql():
    sql = 'select * from papers where paper_id in ("2002.05709","2003.04297","1708.04552","1911.05722","1905.09272","1412.6980","1312.6114","1807.03748","1511.06434","2001.07685","1906.05849","1506.02351")'
    rows = db.query_rows_dict(sql)
    print(js.dumps(rows, indent=2))


def execute_sql():
    sql = 'delete from papers where paper_id in ("2002.05709","2003.04297","1708.04552","1911.05722","1905.09272","1412.6980","1312.6114","1807.03748","1511.06434","2001.07685","1906.05849","1506.02351")'
    db.execute_sql(sql)


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


