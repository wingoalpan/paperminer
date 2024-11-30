#!C:\Users\pypy2\AppData\Local\Programs\Python\Python311\python.exe

import os
import re
from datetime import datetime
import arxiv
from googlesearch import search
from difflib import SequenceMatcher
import requests
import urllib3
from bs4 import BeautifulSoup
import json as js
import hashlib

import wingoal_utils.common as cm
from wingoal_utils.common import log

from langchain_community.tools.google_scholar import GoogleScholarQueryRun
from langchain_community.utilities.google_scholar import GoogleScholarAPIWrapper

g_cookies_jar = None


def get_cookies():
    global g_cookies_jar
    if g_cookies_jar is not None:
        return g_cookies_jar
    g_cookies_jar = requests.cookies.RequestsCookieJar()
    cookies = '_gcl_au=1.1.847313672.1730167061; _ga=GA1.1.1808550103.1730167061; _fbp=fb.1.1730167062411.733566779294549914; _ga_V8XKN0510H=GS1.1.1730167061.1.1.1730172001.60.0.0; _rdt_uuid=1730167062141.376b80b5-923c-489e-9c70-bd7e3752a77f; CFID=49951862; CFTOKEN=bca128ef5126ff5c-34B6A71E-9B97-E439-8D09A1EC70352E47; _ga_N77RQK6L8Y=GS1.1.1730960270.4.1.1730960943.0.0.0; JSESSIONID=B4B822AA120A2AD700BF55F57669DC6E.vts'
    for cookie in cookies.split(';'):
        key, value = cookie.split('=', 1)
        g_cookies_jar.set(key, value)


def text_similarity(ref, tgt):
    a = 0.9  # 完全匹配部分的权重
    min_len = min(len(ref), len(tgt))
    main_similarity = SequenceMatcher(None, ref[:min_len], tgt[:min_len]).ratio()
    ex_similarity = SequenceMatcher(None, ref, tgt).ratio()
    return main_similarity*a + ex_similarity*(1-a)


def get_arxiv_paper_by_id(paper_id, downloads_dir='../papers', download_pdf=False):
    status = {'source': 'arXiv'}
    arxiv_id = paper_id[len('arXiv_'):] if paper_id.startswith('arXiv_') else paper_id
    client = arxiv.Client()
    try:
        arxiv_search = arxiv.Search(id_list=[arxiv_id])
        paper = next(client.results(arxiv_search))
    except Exception as e:
        log(f'Exception caught in get_arxiv_paper_by_id(): {e}')
        status['fail_network'] = True
        return status
    if not paper:
        status['fail_arxiv_id_match'] = True
        return status
    http_prefix = 'http://arxiv.org/abs/'
    arxiv_id_v = paper.entry_id[len(http_prefix):] if paper.entry_id.startswith(http_prefix) else paper.entry_id[len(http_prefix)+1:]
    status['source'] = 'arXiv'
    status['arxiv_id'] = arxiv_id
    status['arxiv_id_v'] = arxiv_id_v
    status['weblink'] = paper.entry_id
    status['doclink'] = paper.pdf_url
    status['verified_title'] = paper.title
    status['authors'] = [author.name for author in paper.authors]
    status['abstract'] = paper.summary
    status['publish_date'] = datetime.strftime(paper.published, '%Y-%m-%d')

    title_fn = re.sub(r'[\\\/:*?"<>|]', '-', paper.title)
    paper_pdf_file = f'{arxiv_id_v}({title_fn}).pdf'
    status['paper_pdf'] = paper_pdf_file
    if download_pdf:
        if not os.path.exists(os.path.join(downloads_dir, paper_pdf_file)):
            print(f'Downloading paper from {paper.entry_id} ...')
            paper.download_pdf(dirpath=downloads_dir, filename=paper_pdf_file)
            status['download_at'] = cm.time_str()
    return status


def get_arxiv_paper_by_title(title, downloads_dir='../papers', download_pdf=False):
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
        log(f'Exception caught in get_arxiv_paper_by_title(): {e}')
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
        _similarity = text_similarity(title.lower(), _searched_title.lower())
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
        status['fail_googl_search'] = True
        return status
    sorted_candidates = sorted(candidates.items(), key=lambda x: x[1][1], reverse=True)
    print(sorted_candidates)
    # 缺省设置失败原因为 fail_arxiv_match。如果arxiv匹配成功，则会返回arxiv的匹配结果。
    status['fail_arxiv_title_match'] = True
    # 选择 title相似度大于 0.7的top2的结果，进一步从arXiv网站进行验证
    selected_candidates = [candidate for candidate in sorted_candidates[:2] if candidate[1][1] > 0.7]
    for candidate in selected_candidates:
        best_arxiv_id, (searched_title, _, additions) = candidate
        candidate_status = get_arxiv_paper_by_id(best_arxiv_id, download_pdf=download_pdf)
        arxiv_similarity = text_similarity(title.lower(), candidate_status['verified_title'].lower())
        if arxiv_similarity > 0.95:
            candidate_status['input_title'] = title
            candidate_status['searched_title'] = searched_title
            candidate_status['publisher'] = additions.get('publisher', '')
            if not candidate_status.get('publish_date', None):
                candidate_status['publish_date'] = additions.get('publish_date', '')
            candidate_status['citations'] = additions.get('citations', '')
            candidate_status['is_partial_title'] = additions.get('is_partial_title', False)
            candidate_status['arxiv_id'] = best_arxiv_id
            candidate_status['similarity'] = arxiv_similarity
            if not status or status.get('similarity', 0.) < arxiv_similarity:
                status = candidate_status
    return status


headers ={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'zh-CN,zh;q=0.9'
}


def get_gscholar_paper_by_title(title, downloads_dir='../papers', download_pdf=False):
    status = {'source': 'GoogleScholar'}
    url_title = title.replace(' ', '+')
    url = f'https://scholar.google.com/scholar?hl=zh-CN&as_sdt=0%2C5&q={url_title}&btnG='
    print(url)
    #proxy = urllib3.ProxyManager('http://127.0.0.1:7890/')
    #response = proxy.request('GET', url, headers=headers)
    #soup = BeautifulSoup(response.data, 'html5lib')
    response = requests.get(url, headers=headers, cookies=get_cookies())
    if response.status_code != 200:
        log(f'http request failed (status_code={response.status_code})')
        status['fail_network'] = response.status_code
        status['status_code'] = response.status_code
        return status
    soup = BeautifulSoup(response.text, 'html5lib')
    #with open('test_scholar_paper_helmholtz_machine.html', 'w', encoding='utf-8') as f:
    #    f.write(soup.prettify())
    results = soup.select('div.gs_r[data-rp]')
    if len(results) == 0:
        status['fail_network'] = True
        return status

    candidates = []
    for result in results:
        no = result.get('data-rp')
        #tag_title = result.find('h3', class_='gs_rt')
        tag_title = result.select_one('h3.gs_rt > a')
        tag_link = result.select_one('h3.gs_rt > a')
        # 如果是引用，<h3>下不会有<a>子标签，
        # example: [引用] High-fidelity performance metrics for generative models in pytorch, 2020
        if not tag_link:
            continue
        tag_desc = result.find('div', class_='gs_rs')
        tag_authors = result.find('div', class_='gs_a')
        tag_doc_link = result.select_one('div.gs_or_ggsm > a')
        tag_doc_type = result.select_one('div.gs_or_ggsm > a > span')
        tag_cite_as = result.find('div', attrs={'class': re.compile(r'gs_fl gs_flb')}).find_all('a')
        tag_cite = tag_cite_as[2] if tag_cite_as and len(tag_cite_as) >= 3 else None
        # get data from the html element
        doc_link = tag_doc_link['href'] if tag_doc_link else ''
        doc_type = tag_doc_type.text.strip() if tag_doc_type else ''
        doc_type = doc_type[1:-1] if doc_type else doc_type  # doc_type 去[]
        doc_name = doc_link.split('/')[-1] if doc_link and doc_type == 'PDF' else ''
        doc_name = '' if not doc_name.endswith('pdf') else doc_name  # doc_name 只保留link为直接pdf文件的场景
        weblink = tag_link['href']
        citations = 0
        if tag_cite:
            m = re.findall(r'[\d]+', tag_cite.text.strip())
            if m:
                citations = int(m[0])
        searched_title = tag_title.text.strip()
        similarity = text_similarity(title.lower(), searched_title.lower())
        h = hashlib.sha256()
        h.update(searched_title.encode('utf-8'))
        paper_id_alike = searched_title[:13].replace(' ', '_') + '_' + h.hexdigest()[:6]
        paper_id = re.sub(r'[\\\/:*?"<>|]', '_', paper_id_alike)

        # A Stuhlmüller, J Taylor… - Advances in neural …, 2013 - proceedings.neurips.cc
        m = re.findall(r'\s(\d{4})\s-', tag_authors.text.strip())
        publish_date = 'Y' + m[-1] if m else ''
        # store data in dictionary
        candidate = {
            'no': no,
            'source': 'GoogleScholar',
            'paper_id': paper_id,
            'searched_title': searched_title,
            'abstract': tag_desc.text.strip(),
            'authors': tag_authors.text.strip(),
            'weblink': weblink,
            'doclink': doc_link,
            'citations': citations,
            'publish_date': publish_date,
            'doc_type': doc_type,
            'doc_name': doc_name,
            'doc_link': doc_link,
            'similarity': similarity
        }
        candidates.append(candidate)
    if not candidates:
        title_fn = re.sub(r'[\\\/:*?"<>|]', '-', title)
        cache_html_file = f'logs/{title_fn}.html'
        with open(cache_html_file, 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        status['fail_google_scholar'] = True
        return status
    sorted_candidates = sorted(candidates, key=lambda x: x['similarity'], reverse=True)
    print(sorted_candidates)
    if sorted_candidates[0]['similarity'] < 0.95:
        status['fail_title_match'] = True
        return status
    status = sorted_candidates[0]
    verified_title = status['searched_title']
    # construct paper_pdf
    title_fn = re.sub(r'[\\\/:*?"<>|]', '-', verified_title)
    paper_pdf_file = f'{status["paper_id"]}({title_fn}).pdf'
    status['verified_title'] = verified_title
    status['paper_pdf'] = paper_pdf_file
    if download_pdf and not os.path.exists(os.path.join(downloads_dir, paper_pdf_file)):
        download_url = status['doc_link']
        if download_url.endswith('.pdf'):
            print(f'Downloading paper from {download_url} ...')
            if download_file(download_url, downloads_dir, paper_pdf_file):
                status['download_at'] = cm.time_str()
    return status


def verify_paper(paper_id=None, paper_name=None, download_pdf=False):
    status = dict()
    if not paper_id and not paper_name:
        print('WARN: at least one of paper_id and paper_name is valid')
        return status
    if paper_id and paper_id.startswith('arXiv_'):
        status = get_arxiv_paper_by_id(paper_id, download_pdf=download_pdf)
    # 如果不存在ref_id，或者ref_id校验失败，则尝试用 ref_title 进行校验
    if not status.get('verified_title', None) and paper_name:
        status = get_arxiv_paper_by_title(paper_name, download_pdf=download_pdf)
    # 如果用 ref_title 在arXiv校验也失败，则尝试用 ref_title 在google scholar进行校验
    if not status.get('verified_title', None) and paper_name:
        status = get_gscholar_paper_by_title(paper_name, download_pdf=download_pdf)
    return status


def download_file(download_url, downloads_dir, paper_pdf_file):
    try:
        pdf_path = os.path.join(downloads_dir, paper_pdf_file)
        f = requests.get(download_url, headers=headers, cookies=get_cookies())
        with open(pdf_path, 'wb') as pdf:
             pdf.write(f.content)
        return True
    except Exception as e:
        pass
    return False


def download_arxiv_pdf(paper_id, downloads_dir, paper_pdf_file):
    arxiv_id = paper_id[len('arXiv_'):] if paper_id.startswith('arXiv_') else paper_id
    client = arxiv.Client()
    arxiv_search = arxiv.Search(id_list=[arxiv_id])
    paper = next(client.results(arxiv_search))
    if paper:
        paper.download_pdf(dirpath=downloads_dir, filename=paper_pdf_file)
        return True
    return False


def download_paper(paper, downloads_dir):
    paper_pdf = paper['paper_pdf']
    paper_id = paper['paper_id']
    pdf_path = os.path.join(downloads_dir, paper_pdf)
    if os.path.exists(pdf_path):
        return True
    if paper_id.startswith('arXiv_'):
        log(f'Downloading paper pdf from arXiv [{paper_id}] ...')
        return download_arxiv_pdf(paper_id, downloads_dir, paper_pdf)
    else:
        doclink = paper['doclink']
        if doclink:
            log(f'Downloading file from {doclink} ...')
            return download_file(doclink, downloads_dir, paper_pdf)
    return False


def download_content(download_url):
    try:
        f = requests.get(download_url, headers=headers, cookies=get_cookies())
        return f.content
    except Exception as e:
        log(f'download_content(): Exception Caught: {e}')
        pass
    return None


def main():
    status = get_gscholar_paper_by_title('Sur la théorie du mouvement brownien')
    # Volumetric Semantic Segmentation Using Pyramid Context Features
    # Recursive deep models for semantic compositionality over a sentiment treebank
    # 488 should be OK: The helmholtz machine
    #status = get_gscholor_paper_by_title('AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration')
    print(js.dumps(status, indent=2))


if __name__ == "__main__":
    main()