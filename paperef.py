#!C:\Users\pypy2\AppData\Local\Programs\Python\Python311\python.exe

import re
import pdfpaper as pp
from wingoal_utils.common import log


def _get_title_id_addition(ref_desc):
    title = ''
    addition = ''
    ref_id = ''
    # example: Thomas Hofmann. 1999. Probabilistic latent semantic analysis. In UAI. [arXiv_2010.09233, ref no:8]
    # example: Diederik P. Kingma and Max Welling. 2014b. Auto-encoding variational bayes. CoRR, abs/1312.6114. [arXiv_2010.09233, ref no:14]
    # example: [3] Bengio, Y., Mesnil, G., Dauphin, Y., and Rifai, S. (2013a). Better mixing via deep representations. In
    # ICML’13. [arXiv_1406.2661, ref no:2]
    year_pat = r'(?P<year>[\(]?[\d]{4}[a-z]?[\)]?)\.\s'
    # example: [2] J. Donahue, P. Krähenbühl, and T. Darrell, “Adversarial feature learning,” arXiv preprint arXiv:1605.09782, 2016.
    title_pat1 = r'(?P<title>([“][\w\W\s\S]*[”]))'
    arxiv_pat = r'(arxiv|arXiv|abs)[\W]+(?P<arxiv_no>\d{4}.\d{4,5})[\s\,\.]'

    year = None
    m = re.match(year_pat, ref_desc)
    if m:
        year = m.group('year')
        ref_desc = ref_desc[len(year + '. '):]
    m = re.findall(arxiv_pat, ref_desc)
    if m:
        ref_id = f'arXiv_{m[0][1]}'

    m = re.findall(title_pat1, ref_desc)
    if m:
        title_with_quotes = m[0][0]
        title = title_with_quotes[1:-1].strip(',')
        pos = ref_desc.find(title_with_quotes)
        if pos == 0:
            addition = ref_desc[pos+len(title_with_quotes):].strip()
            return title, addition, ref_id
    # 57. Zhang, L., Qi, G.J., Wang, L., Luo, J.: Aet vs. aed: Unsupervised representation learning by auto-encoding transformations rather than data.
    if ' vs. ' in ref_desc:
        ref_desc = ref_desc.replace(' vs. ', ' vs_ ')
    for terminate_tag in ['?', '!', '.']:
        title_terminate_tag = terminate_tag + ' '
        if title_terminate_tag in ref_desc:
            parts = ref_desc.split(title_terminate_tag)
            title = parts[0] + terminate_tag.strip('.')
            year = year.lstrip('(').rstrip(')') if year else ''
            if len(parts) >= 2:
                addition = ref_desc[len(title)+1:].strip() + (f' [{year}]' if year else '')
            else:
                addition = f'[{year}]' if year else ''
            return title, addition, ref_id
    title = ref_desc.strip('.').replace(' vs_ ', ' vs. ')
    return title, addition, ref_id


# 法语变音符号
# é è ê ë î ï ù û ü à â ä ô ö ç
# É È Ê Ë Î Ï Ù Û Ü À Â Ä Ô Ö Ç
# 1.闭音符(accent aigu ´)
# 2.开音符(accent grave `)
# 3.长音符(accent circonflexe ˆ)
# 4.分音符(accent tréma ¨)
# 软音符(cédille ¸)

french_umlauts = ['´', '`', 'ˆ', '¨', '˜', '¸']
french_letters = ['é', 'è', 'ê', 'ë', 'í', 'ì', 'î', 'ï', 'ú', 'ù', 'û', 'ü', 'á', 'à', 'â', 'ä', 'ô', 'ö', 'ç',
                  'É', 'È', 'Ê', 'Ë', 'Í', 'Ì', 'Î', 'Ï',      'Ù', 'Û', 'Ü',      'À', 'Â', 'Ä', 'Ô', 'Ö', 'Ç']
#áýÿñòóù
en_fr_map = {
    '´e':'é', '´E':'É',                                         '´a':'á',
    '`e':'è', '`E':'È',                     '`u':'ù', '`U':'Ù', '`a':'à', '`A':'À',
    'ˆe':'ê', 'ˆE':'Ê', 'ˆi':'î', 'ˆI':'Î', 'ˆu':'û', 'ˆU':'Û', 'ˆa':'â', 'ˆA':'Â', 'ˆo':'ô', 'ˆO':'Ô',
    '¨e':'ë', '¨E':'Ë', '¨i':'ï', '¨I':'Ï', '¨u':'ü', '¨U':'Ü', '¨a':'ä', '¨A':'Ä', '¨o':'ö', '¨O':'Ö',
                                                                '˜a':'ã', '˜A':'Ã', '˜o':'õ', '˜O':'Õ',
    'c¸':'ç', 'C¸': 'Ç'
}


def letter_en2fr(text):
    transferred_text = text
    pat_fr = r'(?P<fr_ch>([´`ˆ¨˜][A-Za-z])|([A-Za-z][¸]))'
    m = re.findall(pat_fr, text)
    if m:
        fr_chs = [group[0] for group in m]
        for fr_ch in fr_chs:
            transferred_text = transferred_text.replace(fr_ch, en_fr_map[fr_ch]) if fr_ch in en_fr_map.keys() else transferred_text
    return transferred_text


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


def _check_authors_candidate(ref_text, authors_candidate):
    legal_terminators = [',', ':', ', and', 'and', ', &', '&']
    author_idx = 0
    author = authors_candidate[author_idx]
    ch_idx = 0
    separator = ''
    pos = 0
    last_poses = []
    # example: [YdC19] Dani Yogatama, Cyprien de Masson d’Autume, Jerome Connor, Tomas Kocisky, Mike Chrzanowski, Lingpeng Kong, Angeliki Lazaridou, Wang Ling, Lei Yu, Chris Dyer, et al. Learning and evaluating general linguistic intelligence. arXiv preprint arXiv:1901.11373, 2019.
    new_ref_text = ref_text.replace("d’", 'D-')
    # example: Misha Denil, Babak Shakibi, Laurent Dinh, Marc’Aurelio Ranzato, and Nando de Freitas. Predicting parameters in deep learning, 2014.
    new_ref_text = new_ref_text.replace("’", ' ')
    for ch in new_ref_text:
        pos += 1
        if ch == author[ch_idx]:
            if ch_idx == 0:
                if author_idx > 0:
                    terminator = separator.strip()
                    if terminator not in legal_terminators:
                        break
                separator = ''
            ch_idx += 1
            if ch_idx >= len(author):
                last_poses.append(pos)
                author_idx += 1
                if author_idx >= len(authors_candidate):
                    break
                author = authors_candidate[author_idx]
                ch_idx = 0
        elif ch == '‘':
            continue
        elif ch_idx == 0:
            separator = separator + ch
        elif author_idx == 0:
            ch_idx = 0
        else:
            print(f'Mismatch authors and ref text!')
            break
    last_pos = last_poses[-1]
    authors = authors_candidate[:author_idx]
    # Parry, M., Dawid, A. P., Lauritzen, S., and Others. Proper local scoring rules. The Annals of Statistics, 40(1):561– 592, 2012.
    # 按当前逻辑 解析出来的作者 “Others. Proper” 是无效的
    author = authors[-1]
    if author[-1] not in ['.', ':'] and ref_text[last_pos] not in ['.', ',', ':']:
        author_idx -= 1
        if author_idx > 0:
            last_pos = last_poses[-2]
            authors = authors_candidate[:author_idx]
        else:
            return [], ''
    ref_desc = ref_text[last_pos:].strip()
    ref_desc = ref_desc.lstrip('.').lstrip(',').lstrip(':').strip()
    # Parry, M., Dawid, A. P., Lauritzen, S., and Others. Proper local scoring rules. The Annals of Statistics, 40(1):561– 592, 2012.
    # [14] A. Dosovitskiy, L. Beyer, A. Kolesnikov, D. Weissenborn, X. Zhai, T. Unterthiner, M. Dehghani, M. Minderer, G. Heigold, S. Gelly, et al., “An image is worth 16x16 words: Transformers for image recognition at scale,” arXiv preprint arXiv:2010.11929, 2020.
    # 27. Krizhevsky, A., Hinton, G., et al.: Learning multiple layers of features from tiny images (2009)
    if ref_desc.startswith('et al') or ref_desc.startswith('and'):
        prev_tail = ref_desc.split('.')[0]
        ref_desc = ref_desc[len(prev_tail)+1:].strip(',').strip(':').strip()
    return authors, ref_desc


def _purify_ref_text(ref_line):
    pat = r'(?P<prefix>(\[[\S]+\]\s)|([\d]+\.\s))[\w]+'
    # example: Kamran Kowsari, Donald E Brown, Mojtaba Heidarysafa, Kiana Jafari Meimandi, , Matthew S Gerber, and Laura E Barnes.
    # 2017. Hdltex: Hierarchical deep learning for text classi\ufb01cation.
    # In Machine Learning and Applications (ICMLA), 2017 16th IEEE International Conference on. IEEE. [[arXiv_2010.09233, ref no:15]]
    ref_text = ref_line.replace(', , ', ', ').strip()
    m = re.match(pat, ref_text)
    if m:
        prefix = m.group('prefix')
        return ref_text[len(prefix):]
    else:
        return ref_text

def get_ref_base_data(ref_line):
    nrec = dict()
    ref_text = _purify_ref_text(ref_line)
    authors_candidates = _extract_authors_candidates(ref_text)
    authors = []
    ref_desc = ''
    for authors_candidate in authors_candidates:
        _authors, _ref_desc = _check_authors_candidate(ref_text, authors_candidate)
        if len(_authors) > len(authors):
            authors = _authors
            ref_desc = _ref_desc
    # 处理特殊情况：example: [14] Google. Cloud TPU. https://cloud.google.com/tpu/, 2019.
    if not authors:
        authors_text = ref_text.split('. ')[0]
        ref_desc = ref_text[len(authors_text)+2:].strip()
        m = re.findall(r'\[\w+\]([\S\s]+)', authors_text)
        if m:
            authors = [m[0].strip().strip('.')]
        else:
            authors = [authors_text.strip().strip('.')]
    if authors:
        title, addition, ref_id = _get_title_id_addition(ref_desc)
        nrec['ref_authors'] = authors
        nrec['ref_title'] = title
        nrec['addition'] = addition
        nrec['ref_id'] = ref_id
    return nrec


def get_paper_refs(pdf_path):
    ref_rows = []
    pdf_pages = pp.parse_pdf(pdf_path)
    log(f'total pages = {len(pdf_pages)}')
    refs = pp.parse_refs(pdf_pages)
    # print(f'DEBUG: {refs}')
    log(f'total {len(refs)} references raw text discerned')
    for ref_no, ref_text in refs:
        nrec = get_ref_base_data(ref_text)
        nrec['ref_no'] = ref_no
        nrec['ref_text'] = ref_text
        ref_rows.append(nrec)

    return ref_rows


