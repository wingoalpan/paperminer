#!C:\Users\pypy2\AppData\Local\Programs\Python\Python311\python.exe

import os
import time
import json as js
from enum import Enum
import sys
sys.path.append(os.path.dirname(__file__))
import wingoal_utils.common as cm
import papersearch as ps
import paperdb as db
import paperef
from wingoal_utils.common import (
    load_json,
    log
)


def read_paper_dir_config():
    config_file = os.path.join(os.path.dirname(__file__), 'config.json')
    if os.path.exists(config_file):
        config = load_json(config_file)
        papers_dir = config.get('papers_dir', None)
        if papers_dir and os.path.exists(papers_dir):
            return os.path.abspath(papers_dir)
    return os.path.join(os.path.dirname(__file__), '../papers')


g_papers_pdf_dir = read_paper_dir_config()


class RetCode(Enum):
    Success = 1
    Fail = 2
    Pending = 3
    Retry = 4
    NetworkFail = 5


def set_papers_pdf_dir(papers_pdf_dir):
    global g_papers_pdf_dir
    g_papers_pdf_dir = papers_pdf_dir


def get_papers_pdf_dir():
    return g_papers_pdf_dir


def complete_paper_data(max_refs_num=-1, start=0):
    papers = db.table_rows_dict('papers')
    papers_processing = papers[start:] if max_refs_num <= 0 else papers[start:start+max_refs_num]
    no = start
    for row in papers_processing:
        no += 1
        # 如果weblink有填充，则说明该paper已经完成补齐操作
        if row['abstract']:
            continue
        paper_id = row['paper_id']
        log(f'updating paper {no} [{paper_id}] ....')
        if row['paper_id'].startswith('arXiv_'):
            status = ps.get_arxiv_paper_by_id(paper_id)
            if status:
                row['paper_name'] = status.get('verified_title', '')
                row['arxiv_id_v'] = status.get('arxiv_id_v', '')
                row['weblink'] = status.get('weblink', '')
                row['doclink'] = status.get('doclink', '')
                row['paper_pdf'] = status.get('paper_pdf', '')
                row['authors'] = status.get('authors', '') if not row['authors'] else row['authors']
                row['abstract'] = status.get('abstract', '') if not row['abstract'] else row['abstract']
                row['publish_date'] = status.get('publish_date', '') if not row['publish_date'] else row['publish_date']
                row['download_at'] = status.get('download_at', '') if not row['download_at'] else row['download_at']
                row['update_at'] = cm.time_str()
                row['status'] = 'Verified'
                db.update('papers', row, 'paper_id')
                log(f'updated paper {no}: {paper_id}')
        else:
            status = ps.get_gscholar_paper_by_title(row['paper_name'])
            if status:
                row['citations'] = status.get('citations', None)
                # row['authors'] = row['authors'] if row['authors'] else status.get('authors', '')
                row['abstract'] = row['abstract'] if row['abstract'] else status.get('abstract', '')
                row['publish_date'] = status.get('publish_date', '')
                # row['arxiv_id_v'] = row['arxiv_id_v'] if row['arxiv_id_v'] else status.get('arxiv_id_v', '')
                row['weblink'] = row['weblink'] if row['weblink'] else status['weblink']
                row['doclink'] = row['doclink'] if row['doclink'] else status['doclink']
                row['paper_pdf'] = row['paper_pdf'] if row['paper_pdf'] else status['paper_pdf']
                row['download_at'] = row['download_at'] if row['download_at'] else status.get('download_at', None)
                row['update_at'] = cm.time_str()
                row['status'] = 'Verified'
                db.update('papers', row, 'paper_id')
                log(f'updated paper {no}: {paper_id}')


def verify_reference(ref, papers, drill=False):
    ref_id = ref['ref_id']
    # 如果该reference已经来papers表中了, 则以papers数据为基线更新refs
    if ref_id and ref_id in papers.keys():
        ref['ref_title'] = papers[ref_id]['paper_name']
        ref['verified_title'] = papers[ref_id]['paper_name']
        ref['verify_at'] = cm.time_str()
        ref['update_at'] = cm.time_str()
        if drill:
            print(js.dumps(ref, indent=2))
        else:
            db.update('refs', ref, 'id')
        return RetCode.Success
    # 用 ref_id 或 ref_title 从google和arxiv网站进行校验。
    # ref_id 标准化
    if ref_id and ref_id.startswith('[arxiv]'):
        ref_id = 'arXiv_' + ref_id[len('[arxiv]'):]
    status = ps.verify_paper(ref_id, ref['ref_title'])
    # 参数无效，导致返回空状态
    if not status:
        return RetCode.Retry

    # 网络原因校验失败，稍后重试
    if status.get('fail_network', None):
        return RetCode.NetworkFail

    # 如果校验成功，则先更新 papers表，再更新 refs表
    if status.get('verified_title', None):
        if status['source'] == 'arXiv':
            ref_id = 'arXiv_' + status['arxiv_id']
        elif status['source'] == 'GoogleScholar':
            ref_id = 'GS_' + status['paper_id']
        if ref_id in papers.keys():
            # 更新 paper引用计数
            paper = papers[ref_id]
            paper['citations'] = paper['citations'] if paper['citations'] else status.get('citations', None)
            paper['authors'] = paper['authors'] if paper['authors'] else status.get('authors', '')
            paper['abstract'] = paper['abstract'] if paper['abstract'] else status.get('abstract', '')
            paper['publish_date'] = paper['publish_date'] if paper['publish_date'] else status.get('publish_date', '')
            paper['arxiv_id_v'] = paper['arxiv_id_v'] if paper['arxiv_id_v'] else status.get('arxiv_id_v', '')
            paper['weblink'] = paper['weblink'] if paper['weblink'] else status['weblink']
            paper['doclink'] = paper['doclink'] if paper['doclink'] else status['doclink']
            paper['paper_pdf'] = paper['paper_pdf'] if paper['paper_pdf'] else status['paper_pdf']
            paper['download_at'] = paper['download_at'] if paper['download_at'] else status.get('download_at', None)
            paper['update_at'] = cm.time_str()
            paper['status'] = 'Verified'
            if drill:
                print('update paper: ', js.dumps(paper, indent=2))
            else:
                db.update('papers', paper, 'paper_id')
        else:
            new_paper = dict()
            new_paper['paper_id'] = ref_id
            new_paper['paper_name'] = status['verified_title']
            new_paper['authors'] = ref['ref_authors']
            new_paper['authors'] = str(status.get('authors', ''))
            new_paper['abstract'] = status.get('abstract', '')
            new_paper['publish_date'] = status.get('publish_date', '')
            new_paper['arxiv_id_v'] = status.get('arxiv_id_v', '')
            new_paper['weblink'] = status['weblink']
            new_paper['doclink'] = status['doclink']
            new_paper['paper_pdf'] = status['paper_pdf']
            new_paper['citations'] = status.get('citations', None)
            new_paper['download_at'] = status.get('download_at', None)
            new_paper['create_at'] = cm.time_str()
            new_paper['update_at'] = cm.time_str()
            new_paper['status'] = 'Verified'
            if drill:
                print('add new paper: ', js.dumps(new_paper, indent=2))
            else:
                db.import_data('papers', [new_paper], 'paper_id', is_dict=True)
            # 新增数据库papers 表记录后，同步更新内存 papers_dict
            papers[ref_id] = new_paper
        ref['ref_id'] = ref_id
        ref['ref_title'] = status['verified_title']
        ref['verified_title'] = status['verified_title']
        ref['status'] = 'Verify OK!'
        ref['verify_at'] = cm.time_str()
        ref['update_at'] = cm.time_str()
        if drill:
            print('update reference: ', js.dumps(ref, indent=2))
        else:
            db.update('refs', ref, 'id')
    else:
        ref['status'] = 'GS sVerify Failed!'
        ref['verify_at'] = cm.time_str()
        ref['update_at'] = cm.time_str()
        if drill:
            print(js.dumps(ref, indent=2))
        else:
            db.update('refs', ref, 'id')
    return RetCode.Success


def verify_references(max_refs_num=-1, start=0, drill=False):
    # papers数据读入内存 papers_dict中
    papers = db.table_rows_dict('papers')
    papers_dict = cm.diclist2dic(papers, 'paper_id')
    refs = db.table_rows_dict('refs')
    refs_processing = refs[start:] if max_refs_num <=0 else refs[start:start+max_refs_num]
    no = start
    for row in refs_processing:
        no += 1
        log('Verifying ref {no} .... {ref_title} '.format(no=no, ref_title=row['ref_title']))
        # 如果verified_title有填充，则说明该reference已经完成校验操作
        if row['verified_title']:
            continue
        time.sleep(5)
        ret_code = verify_reference(row, papers_dict, drill=drill)
        if ret_code == RetCode.NetworkFail:
            log(f'WARN: the network request maybe rejected by website for too frequent access.')
            break


def extract_references(paper, drill=False):
    downloads_dir = get_papers_pdf_dir()
    paper_pdf = paper['paper_pdf']
    pdf_path = os.path.join(downloads_dir, paper_pdf)
    if not os.path.exists(pdf_path):
        if not ps.download_paper(paper, downloads_dir):
            log('download paper pdf failed!')
            return False
    ref_rows = paperef.get_paper_refs(pdf_path)
    for ref in ref_rows:
        ref['paper_id'] = paper['paper_id']
        ref['paper_name'] = paper['paper_name']
        ref['create_at'] = cm.time_str()
        ref['update_at'] = cm.time_str()
        # 入库前list 转化为 str
        ref['ref_authors'] = str(ref['ref_authors'])
    if drill:
        print(js.dumps(ref_rows, indent=2, ensure_ascii=False))
        print(f'Total {len(ref_rows)} references')
    else:
        db.import_data('refs', ref_rows, ['paper_id', 'ref_no'], is_dict=True)
        # 更新papers表
        paper['parseref_at'] = cm.time_str()
        db.update('papers', paper, 'paper_id')
    log(f'total {len(ref_rows)} references extracted!')
    return ref_rows


def extract_papers_references(max_refs_num=-1, start=0, drill=False):
    downloads_dir = 'E:\\panyungao\\ml\\papers'
    papers = db.table_rows_dict('papers')
    papers_processing = papers[start:] if max_refs_num <= 0 else papers[start:start+max_refs_num]
    no = start
    for row in papers_processing:
        no += 1
        if row['parseref_at']:
            continue
        print(f'{no}: paper_id = {row["paper_id"]}')
        paper_pdf = row['paper_pdf']
        pdf_path = os.path.join(downloads_dir, paper_pdf)
        if not os.path.exists(pdf_path):
            if not ps.download_paper(row, downloads_dir):
                continue
        ref_rows = paperef.get_paper_refs(pdf_path)
        for ref in ref_rows:
            ref['paper_id'] = row['paper_id']
            ref['paper_name'] = row['paper_name']
            ref['create_at'] = cm.time_str()
            ref['update_at'] = cm.time_str()
            # 入库前list 转化为 str
            ref['ref_authors'] = str(ref['ref_authors'])
        if drill:
            print(js.dumps(ref_rows, indent=2))
        else:
            db.import_data('refs', ref_rows, is_dict=True)
            # 更新papers表
            row['parseref_at'] = cm.time_str()
            db.update('papers', row, 'paper_id')


def _status2paper(status):
    if not status:
        return None
    if status['source'] == 'arXiv':
        paper_id = 'arXiv_' + status['arxiv_id']
        authors = str(status['authors'])
    else:
        paper_id = 'GS_' + status['paper_id']
        authors = None
    paper = dict()
    paper['paper_id'] = paper_id
    paper['paper_name'] = status['verified_title']
    paper['authors'] = authors
    paper['abstract'] = status.get('abstract', '')
    paper['publish_date'] = status.get('publish_date', '')
    paper['arxiv_id_v'] = status.get('arxiv_id_v', '')
    paper['weblink'] = status['weblink']
    paper['paper_pdf'] = status['paper_pdf']
    paper['citations'] = status.get('citations', None)
    paper['download_at'] = status.get('download_at', None)
    paper['create_at'] = cm.time_str()
    paper['update_at'] = cm.time_str()
    paper['status'] = 'Verified'
    return paper


def analyze_paper(paper_id, paper_name, verbose=False):
    if paper_id:
        paper_list = db.table_conditions('papers', {'paper_id': paper_id})
        log(f'query paper information from database: paper_id={paper_id}')
    else:
        paper_list = db.table_conditions('papers', {'paper_name': paper_name})
        log(f'query paper information from database: paper_name={paper_name}')
    paper = paper_list[0] if paper_list else None
    if not paper or not paper['abstract']:
        log(f'verify paper from arxiv or google scholar ...')
        status = ps.verify_paper(paper_id, paper_name, download_pdf=True)
        new_paper = _status2paper(status)
        new_paper['authors'] = paper['authors'] if paper and paper.get('authors', None) else new_paper['authors']
        db.insert_or_update('papers', new_paper, 'paper_id')
        paper_id = new_paper['paper_id']
        paper = db.table_conditions('papers', {'paper_id': paper_id})[0]
    if not paper['parseref_at']:
        log(f'extract reference from the paper pdf ...')
        extract_references(paper)
    # verify all references of this paper.
    refs = db.table_conditions('refs', {'paper_id': paper['paper_id']})
    papers_list = db.table_rows_dict('papers')
    papers = cm.diclist2dic(papers_list, 'paper_id')
    for ref in refs:
        if ref['verified_title']:
            continue
        log(f'verify reference [{ref["ref_no"]}] from arxiv or google scholar ... ...')
        ret_code = verify_reference(ref, papers)
        if ret_code == RetCode.NetworkFail:
            log(f'WARN: the network request maybe rejected by website for too frequent access.')
            break
    log(f'analyze paper finished!')
