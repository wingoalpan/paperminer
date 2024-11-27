
import os
import sys
import argparse
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
import paperef as pr


def _extract_authors_candidates(ref_text):
    name_fr_pat = r'((des\s)|(van\s)|(den\s)|(de\s)|(las\s)|(der\s))'
    word_pat = r'(([A-Z][\w\-´`ˆ¨˜¸]+)(-[A-Z][\w\-´`ˆ¨˜¸]+)*)'
    abbr_pat = r'(([A-ZŁ]\.)([\s-]?[A-ZŁa-z]\.)*)'
    words_pat = f'({word_pat}(\s{word_pat})*)'
    pat_words_abbr = f'({name_fr_pat}*{words_pat}\,\s{abbr_pat})'
    pat_abbrs_words = f'({abbr_pat}\s{words_pat})'
    #pat_words_abbr = r'(((des\s)|(van\s)|(den\s)|(de\s)|(las\s))*([A-Z][\w\-´¸¨˜`]+)(\s[A-Z][\w\-´¸¨˜`]+)*\,(\s[A-ZŁ]\.)([\s-][A-Za-z]\.)*)'
    #pat_abbrs_words = r'(([A-Z][a-z]?[\.]?)([\s-][A-Za-zÁ][\.]?)*\s([A-Z][\w\-´¸¨˜`]+)((\svon)|(\sden))*(\s[A-Z][\w\-´¸¨˜`]+)*)'
    pat_word_abbr_word = r'(([A-Z][\w\-´¸¨˜`]+)+\s([A-Za-z][\.]?\s)+([A-Z][\w\-´¸¨˜`]+))'
    pat_words = r'(([A-Z`Ł][\w\-´¸¨˜`]+)(\s[A-Z][\w\-´¸¨˜`]+)+)'
    pat_prep_words = r'(([A-Z][\w\-´¸¨˜`]+\s)+((von\s)|(van\s)|(den\s)|(del\s)|(der\s)|(de\s)|(tau\s))+([A-Z][\w\-´¸¨˜`]+)(\s[A-Z][\w\-´¸¨˜`]+)*)'
    # example: [Mac92] David. MacKay. Information-based objective functions for active data selection. Neural Computation, 1992.
    pat_ex_abbrs_words = r'(([A-Z][\w]+[\.])\s([A-Z][\w\-´¸¨˜`]+))'
    # example: T, P. Convergence condition of the TAP equation for the inﬁnite-ranged Ising spin glass model. J. Phys. A: Math. Gen. 15 1971, 1982.
    pat_ex_words_abbr = r'([A-Z]\,(\s[A-ZŁ]\.)([\s-][A-Za-z]\.)*)'
    # example: MLC-Team. MLC-LLM, 2023. URL https://github. com/mlc-ai/mlc-llm.
    pat_ex_team = r'([A-Z][\w]+\-[A-Z][\w]+)'

    # 增加 & 作为名称间分割符，样例：Multitask_lea_001882(Multitask learning).pdf, ref_no: 4
    # Baluja, S. & Pomerleau, D. A. (1995). \u201cUsing the Representation in a Neural Network\u2019s Hidden Layer for TaskSpeci\ufb01c Focus of Attention,\u201d Proceedings of the International Joint Conference on Arti\ufb01cial Intelligence 1995, IJCAI-95, Montreal, Canada, pp. 133-139.
    pat_author1 = '(' + '|'.join([pat_abbrs_words, pat_words_abbr, pat_prep_words, pat_word_abbr_word,
                                 pat_words, pat_ex_abbrs_words, pat_ex_words_abbr, pat_ex_team]) + ')' \
                      + r'(([\,\s])|(\.\s)|(\sand)|(\s\&)|(\:\s))'
    pat_author2 = '(' + '|'.join([pat_words, pat_words_abbr, pat_abbrs_words, pat_prep_words, pat_word_abbr_word,
                                  pat_ex_abbrs_words, pat_ex_words_abbr, pat_ex_team]) + ')' \
                      + r'(([\,\s])|(\.\s)|(\sand)|(\s\&)|(\:\s))'
    authors_candidates = []

    ref_text = ref_text.replace("d’", 'D-')
    ref_text = ref_text.replace("’", ' ')
    for pat_author in [pat_author1, pat_author2]:
        m = re.findall(pat_author, ref_text)
        if m:
            authors_candidates.append([group[0] for group in m])

    # 针对简单case处理
    # example: [oR16] University of Regensburg. Fascha, 2016.
    # example: [HB20] Daniel Hernandez and Tom Brown. Ai and efﬁciency, May 2020.
    if not authors_candidates:
        is_simple_case = False
        if len(ref_text.split('. ')) <= 2 and len(ref_text.split('. ')[0].split(',')) < 2:
            ref_text = ref_text.split('. ')[0] + '. '
            is_simple_case = True

        if is_simple_case:
            m = re.findall(r'\[\w+\]([\S\s]+)', ref_text)
            if m:
                authors_candidates = [[m[0].strip().strip('.')]]
            else:
                authors_candidates = [[ref_text.strip().strip('.')]]
    return authors_candidates


def test_extract_authors_candidates():
    # source: arXiv_1512.03385
    ref_text = '[48] A. Vedaldi and B. Fulkerson. VLFeat: An open and portable library of computer vision algorithms, 2008.'
    # source: arXiv_1512.03385
    ref_text = '[50] M. D. Zeiler and R. Fergus. Visualizing and understanding convolutional neural networks. In ECCV, 2014. 9'
    ref_text = 'Baluja, S. & Pomerleau, D. A. (1995). \u201cUsing the Representation in a Neural Network\u2019s Hidden Layer for TaskSpeci\ufb01c Focus of Attention,\u201d Proceedings of the International Joint Conference on Arti\ufb01cial Intelligence 1995, IJCAI-95, Montreal, Canada, pp. 133-139.'
    authors_candidates = _extract_authors_candidates(ref_text)
    print(authors_candidates)


def main():
    print('')
    test_extract_authors_candidates()


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


