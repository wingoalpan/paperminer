
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
from paperminer import paperef as pr


def _extract_authors_candidates(ref_text):
    name_fr_pat = r'((des\s)|(van\s)|(den\s)|(de\s)|(las\s)|(der\s))'
    word_pat = r'(([A-Z][\w\-´`ˆ¨˜’¸]+)(-[A-Z][\w\-´`ˆ¨˜’¸]+)*)'
    abbr_pat = r'(([A-ZŁ]\.)([\s-]?[A-ZŁa-z]\.)*)'
    words_pat = f'({word_pat}(\s{word_pat})*)'
    pat_words_abbr = f'({name_fr_pat}*{words_pat}\,\s{abbr_pat})'
    pat_abbrs_words = f'({abbr_pat}\s{words_pat})'
    #pat_words_abbr = r'(((des\s)|(van\s)|(den\s)|(de\s)|(las\s))*([A-Z][\w\-´¸¨˜`]+)(\s[A-Z][\w\-´¸¨˜`]+)*\,(\s[A-ZŁ]\.)([\s-][A-Za-z]\.)*)'
    #pat_abbrs_words = r'(([A-Z][a-z]?[\.]?)([\s-][A-Za-zÁ][\.]?)*\s([A-Z][\w\-´¸¨˜`]+)((\svon)|(\sden))*(\s[A-Z][\w\-´¸¨˜`]+)*)'
    pat_word_abbr_word = r'(([A-Z][\w\-´¸¨˜`]+)+\s([A-Za-z][\.]?\s)+([A-Z][\w\-´¸¨˜`]+))'
    pat_words = r'(([A-Z`Ł][\w\-´`ˆ¨˜’¸]+)(\s[A-Z][\w\-´`ˆ¨˜’¸]+)+)'
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
                      + r'(([\,\s])|(\.\s)|(\sand)|(\s\&)|(\:\s)|(\;\s))'
    pat_author2 = '(' + '|'.join([pat_words, pat_words_abbr, pat_abbrs_words, pat_prep_words, pat_word_abbr_word,
                                  pat_ex_abbrs_words, pat_ex_words_abbr, pat_ex_team]) + ')' \
                      + r'(([\,\s])|(\.\s)|(\sand)|(\s\&)|(\:\s)|(\;\s))'
    authors_candidates = []

    pat_author_debug = '(' + '|'.join([pat_words_abbr]) + ')' \
                      + r'(([\,\s])|(\.\s)|(\sand)|(\s\&)|(\:\s)|(\;\s))'

    ref_text = ref_text.replace("d’", 'D-')
    # ref_text = ref_text.replace("’", ' ')
    print(ref_text)
    for pat_author in [pat_author_debug, pat_author2]:
        m = re.findall(pat_author, ref_text)
        if m:
            authors_candidates.append([group[0] for group in m])
    print(authors_candidates)
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
    # ref_text = '[48] A. Vedaldi and B. Fulkerson. VLFeat: An open and portable library of computer vision algorithms, 2008.'
    # source: arXiv_1512.03385
    # ref_text = '[50] M. D. Zeiler and R. Fergus. Visualizing and understanding convolutional neural networks. In ECCV, 2014. 9'
    # ref_text = 'Baluja, S. & Pomerleau, D. A. (1995). \u201cUsing the Representation in a Neural Network\u2019s Hidden Layer for TaskSpeci\ufb01c Focus of Attention,\u201d Proceedings of the International Joint Conference on Arti\ufb01cial Intelligence 1995, IJCAI-95, Montreal, Canada, pp. 133-139.'
    # 来源：Ethical_Consi_29749c(Ethical Considerations of Generative AI- A Survey Exploring the Role of Decision Makers in the Loop).pdf
    # ref_text = 'Vaswani, A.; Shazeer, N.; Parmar, N.; Uszkoreit, J.; Jones, L.; Gomez, A. N.; Kaiser, Ł.; and Polosukhin, I. 2017. Attention is all you need. Advances in neural information processing systems, 30.'
    ref_text = 'Dunphy, E. J.; Conlon, S. C.; O’Brien, S. A.; Loughrey, E.; and O’Shea, B. J. 2016. End-of-life planning with frail patients attending general practice: an exploratory prospective cross-sectional study. British Journal of General Practice, 66(650): e661–e666.'
    authors_candidates = pr._extract_authors_candidates(ref_text)
    print(authors_candidates)


def test_get_ref_base_data():
    # ref_text = 'Dunphy, E. J.; Conlon, S. C.; O’Brien, S. A.; Loughrey, E.; and O’Shea, B. J. 2016. End-of-life planning with frail patients attending general practice: an exploratory prospective cross-sectional study. British Journal of General Practice, 66(650): e661–e666.'
    ref_text = '[KRL08] Koray Kavukcuoglu, Marc’Aurelio Ranzato, and Yann LeCun. Fast inference in sparse coding algorithms with applications to object recognition. Technical Report CBLLTR-2008-12-01, Computational and Biological Learning Lab, Courant Institute, NYU, 2008.'
    authors_candidates = _extract_authors_candidates(ref_text)
    print(js.dumps(authors_candidates, indent=2, ensure_ascii=False))
    nrec = pr.get_ref_base_data(ref_text)
    print(js.dumps(nrec, indent=2, ensure_ascii=False))


def main():
    print('')
    test_get_ref_base_data()


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


