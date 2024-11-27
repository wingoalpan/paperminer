#!C:\Users\pypy2\AppData\Local\Programs\Python\Python311\python.exe

from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTLine
import re
from enum import Enum
from wingoal_utils.common import log

DEFAULT_MIN_Y = 10
DEFAULT_MAX_Y = 780


class RefFormat(Enum):
    REF_NO = 1
    REF_ID = 2
    REF_INDENT = 3
    REF_NUM_DOT = 4


# 从element提取内容主文本（不含装饰文本<横向字符、上标注释字符>）
def text_extraction(element, min_y=DEFAULT_MIN_Y, max_y=DEFAULT_MAX_Y):
    if (element.y1 < min_y) or (element.y0 > max_y):
        return None
    texts = []
    total_font_size = 0
    upright_char_count = 0
    char_count = 0
    # 遍历文本行中的每个字符，统计装饰字符（横向字符、上标/下标注释字符）
    for text_line in element:
        if isinstance(text_line, LTTextContainer):
            # 遍历文本行中的每个字符
            for character in text_line:
                if isinstance(character, LTChar):
                    total_font_size += character.size
                    if character.upright:
                        upright_char_count += 1
                    char_count += 1
    # 如果非文本字符，返回原内容
    if char_count == 0:
        pos = (element.y1, element.x0, element.y0, element.x1)
        return [(pos, element.get_text(), 0)]
    # 如果文本为横向字体，则忽略
    if upright_char_count < char_count:
        return None
    average_font_size = total_font_size/char_count - 1.0
    # 如果文本中包含上标/下标注释字符，则忽略注释字符
    for text_line in element:
        if isinstance(text_line, LTTextContainer):
            line_pos = (text_line.y1, text_line.x0, text_line.y0, text_line.x1)
            line_text = ''
            # 遍历文本行中的每个字符,去噪
            max_font_size = 0
            for character in text_line:
                if isinstance(character, LTChar):
                    if character.size > max_font_size:
                        max_font_size = character.size
                    # 如果文本中不包含上标/下标注释字符，则返回原文本
                    if character.size >= average_font_size:
                        line_text = line_text + character.get_text()
                else:
                    line_text = line_text + character.get_text()
            texts.append((line_pos, line_text, max_font_size))
    return texts


def _merge_line(x0, x1, merge_xs):
    if len(merge_xs) == 0:
        merge_xs.append([x0, x1])
        return
    if x1 < merge_xs[0][0]:
        merge_xs.insert(0, [x0, x1])
        return
    if x0 > merge_xs[-1][1]:
        merge_xs.append([x0, x1])
        return
    adjust_idx = -1
    for i in range(len(merge_xs)):
        seg = merge_xs[i]
        l, h = seg
        if (x0 >= l) and (x1 <= h):
            break
        elif x1 < l:
            merge_xs.insert(i, [x0, x1])
            break
        elif x0 > h:
            continue
        elif (x0 >= l) and (x0 <= h) or (x1 >= l) and (x1 <= h) or (x0 <= l) and (x1 >= h):
            seg[1] = max(x1, h)
            seg[0] = min(x0, l)
            adjust_idx = i
            break
    if adjust_idx < 0:
        return
    l, h = merge_xs[adjust_idx]
    delete_list = []
    for i in range(adjust_idx + 1, len(merge_xs)):
        _l, _h = merge_xs[i]
        if _l <= h:
            delete_list.append(i)
            h = max(h, _h)
    merge_xs[adjust_idx][1] = h
    for i in reversed(delete_list):
        del merge_xs[i]


def _slit_vertical(rects):
    line_segments = []
    for rect in rects:
        y1, x0, y0, x1 = rect
        _merge_line(y0, y1, line_segments)
    return line_segments


def _header_footer_alike(rects):
    y_segments = _slit_vertical(rects)
    top = y_segments[-1]
    bottom = y_segments[0]
    # header_alike_y0 = top[0]
    # footer_alike_y1 = bottom[1]
    return top[0], bottom[1]


def get_header_footer_y(pdf_pages):
    header_alike_ys = []
    footer_alike_ys = []
    for page_no in range(len(pdf_pages)):
        if page_no == 0:
            continue
        text_lines = pdf_pages[page_no][1]
        rects = [rect for rect, _, _ in text_lines]

        header_alike_y0, footer_alike_y1 = _header_footer_alike(rects)
        header_alike_ys.append(header_alike_y0)
        footer_alike_ys.append(footer_alike_y1)
    header_alike_max, header_alike_min = max(header_alike_ys), min(header_alike_ys)
    footer_alike_max, footer_alike_min = max(footer_alike_ys), min(footer_alike_ys)
    header_y = header_alike_min - 1 if header_alike_max - header_alike_min <= 2 else None
    footer_y = footer_alike_max + 1 if footer_alike_max - footer_alike_min <= 2 else None
    return header_y, footer_y


def get_header_footer(text_lines, header_y, footer_y):
    header = []
    footer = []
    for text_line in text_lines:
        y1, x0, y0, x1 = text_line[0]
        if header_y is not None:
            if y0 >= header_y:
                header.append(text_line)
        if footer_y is not None:
            if y1 <= footer_y:
                footer.append(text_line)
    header.sort(key=lambda a: a[0][1])
    footer.sort(key=lambda a: a[0][1])
    return ' '.join([a[1].strip() for a in header]), ' '.join([a[1].strip() for a in footer])


def strip_header_footer(text_lines, header_y, footer_y):
    stripped_text_lines = []
    for text_line in text_lines:
        y1, x0, y0, x1 = text_line[0]
        if header_y is not None:
            if y0 >= header_y:
                continue
        if footer_y is not None:
            if y1 <= footer_y:
                continue
        stripped_text_lines.append(text_line)
    return stripped_text_lines


def _split_line(merge_xs):
    if len(merge_xs) <= 1:
        return 0
    _, r = merge_xs[0]
    for l, h in merge_xs[1:]:
        x_split = (l + r)/2
        if (x_split > 250) and (x_split < 350):
            return (l + r)/2
        r = h
    return 0


def _is_separated(merge_xs, low_bound, up_bound):
    for l, h in merge_xs:
        if l <= low_bound and h >= up_bound:
            return False
    return True


# 获取横向分割线坐标y 和纵向分割线x, 其中：
#    (1) y 将页面分为上下两部分，上面部分为 top_part, 下面为 bottom_part
#    (2) x 将bottom_part分为左右两部分，左面部分为 left_part, 右面部分为 right_part
#    (3) 最终可根据 y, x将页面分割为 top_part, left_part, right_part三部分。
#    (4) 例外说明： 如果bottom_part不能被纵向左右分割，那么页面将也不会上下分割
# 分割规则：
#    1. 分割线必须穿过文本区
#    2. 分割线不能穿过任何文字
#    3. 分割线与文本距离（与所有文字距离最近的那个距离）最大化
def get_split_xy(rects):
    rects.sort(key=lambda a: a[0], reverse=True)
    y_split = 0
    merge_xs = []
    for rect in rects:
        y1, x0, y0, x1 = rect
        if not merge_xs:
            merge_xs.append([x0, x1])
        else:
            _merge_line(x0, x1, merge_xs)
        if not _is_separated(merge_xs, 250, 350):
            merge_xs = []
            y_split = y0 - 15

    x_split = _split_line(merge_xs)
    if (x_split <= 0) or (y_split < 150):
        y_split = 0
    return x_split, y_split


def split_page_to_blocks(page_text_lines):
    page_text_lines.sort(key=lambda a: round(a[0][0]), reverse=True)
    rects = [rect for rect, _, _ in page_text_lines]
    x_fit, y_fit = get_split_xy(rects)
    h_split_row = 0
    top_text_lines = []
    left_text_lines = []
    right_text_lines = []
    new_page_text_lines = []
    if y_fit > 0:
        for rect, text, font_size in page_text_lines:
            y1, _, y0, _ = rect
            if y0 > y_fit:
                h_split_row += 1
                top_text_lines.append([rect, text, font_size])
            else:
                break
    if x_fit > 0:
        for rect, text, font_size in page_text_lines[h_split_row:]:
            x0 = rect[1]
            if x0 < x_fit:
                left_text_lines.append([rect, text, font_size])
            else:
                right_text_lines.append([rect, text, font_size])
    if (x_fit <= 0)  and (y_fit <= 0):
        new_page_text_lines = [[rect, text, font_size] for rect, text, font_size in page_text_lines]
    return [text_lines for text_lines in [top_text_lines, left_text_lines, right_text_lines, new_page_text_lines] if text_lines]


# 文字重新排列，纵坐标（行位置）校正：
# 校正算法：
#    1. 纵坐标y1四舍五入后按纵坐标y1从大到小排序（即从上到下）
#    2. 从前至后遍历所有文本纵坐标y1, 每个文本y1若与前一文本y1只差小于等于1，则更其y1与前一文本y1对齐（更新为前文本y1）
#    3. 所有文本按校正后的 y1坐标（逆序）+ x0坐标（顺序）排序。
def rearrange(_text_lines, sorted_on_y1=True):
    # 如果传入的_text_lines 是没有按y1排序的，则先排序再校正
    if not sorted_on_y1:
        _text_lines.sort(key=lambda a: round(a[0][0]), reverse=True)
    prev_y1 = None
    for text_line in _text_lines:
        if prev_y1 is None:
            prev_y1 = round(text_line[0][0])
        cur_y1 = round(text_line[0][0])
        if prev_y1 - cur_y1 <= 1:
            cur_y1 = prev_y1
        # 添加处理后的坐标，用于排序索引
        text_line.append((cur_y1, 1000-text_line[0][1]))
        prev_y1 = cur_y1
    _text_lines.sort(key=lambda a: [a[3][0], a[3][1]], reverse=True)


def _check_reference_by_no(page_text_lines, ref_font_size, probe_lines=10):
    is_reference_page = False
    pat = r'\[(?P<ref_no>\d*)\] [\s\S]*'
    for i in range(min(probe_lines, len(page_text_lines))):
        text_line = page_text_lines[i][1].strip()
        font_size = page_text_lines[i][2]
        if abs(ref_font_size - font_size) >= 1.0:
            break
        m = re.match(pat, text_line)
        if m:
            is_reference_page = True
            break
    return is_reference_page


def _check_reference_by_num_dot(page_text_lines, ref_font_size, probe_lines=10):
    is_reference_page = False
    pat = r'(?P<ref_no>\d*)\. [\s\S]*'
    for i in range(min(probe_lines, len(page_text_lines))):
        text_line = page_text_lines[i][1].strip()
        font_size = page_text_lines[i][2]
        if abs(ref_font_size - font_size) >= 1.0:
            break
        m = re.match(pat, text_line)
        if m:
            is_reference_page = True
            break
    return is_reference_page


def _check_reference_by_id(page_text_lines, ref_font_size, probe_lines=10):
    is_reference_page = False
    pat = r'\[(?P<ref_id>\S*)\] [\s\S]*'
    for i in range(min(probe_lines, len(page_text_lines))):
        text_line = page_text_lines[i][1].strip()
        font_size = page_text_lines[i][2]
        if abs(ref_font_size - font_size) >= 1.0:
            break
        m = re.match(pat, text_line)
        if m:
            is_reference_page = True
            break
    return is_reference_page


def _check_reference_by_indent(page_text_lines, ref_font_size, probe_lines=10):
    is_reference_page = True
    reference_found = False
    prev_y1, prev_y0 = -1, -1
    ref_start_x = -1
    for i in range(min(probe_lines, len(page_text_lines))):
        font_size = page_text_lines[i][2]
        if abs(ref_font_size - font_size) >= 1.0:
            break
        if prev_y1 < 0:
            prev_y1, ref_start_x, prev_y0, _ = page_text_lines[i][0]
            continue
        cur_y1, cur_x0, cur_y0, _ = page_text_lines[i][0]
        if ref_start_x - cur_x0 > 8:
            ref_start_x = cur_x0
        # 满足reference首行格式规则（不缩进、与前行间距大）
        if prev_y0 - cur_y1 > 8 and cur_x0 - ref_start_x < 4:
            prev_y1, prev_y0 = cur_y1, cur_y0
            reference_found = True
        # 满足reference续行格式规则（缩进、与前行紧挨）
        # 缩进检查阈值由 8 变更为 5， 样例： Multitask_lea_001882(Multitask learning).pdf的reference缩进为 5.9
        elif prev_y0 - cur_y1 < 4 and cur_x0 - ref_start_x > 5:
            prev_y1, prev_y0 = cur_y1, cur_y0
            reference_found = True
        # 疑似最近两行都是续行，重置ref_start_x后继续观察
        elif prev_y0 - cur_y1 < 4 and cur_x0 - ref_start_x < 4:
            prev_y1, prev_y0 = cur_y1, cur_y0
            ref_start_x = cur_x0 - 6
        else:
            is_reference_page = False
            break
    return is_reference_page and reference_found


def _search_reference_start(page_text_lines):
    for i in range(len(page_text_lines)):
        line_text = page_text_lines[i][1].strip()
        # 注释掉下面两行，原因是有些论文 "References" 字号并未增大，例如论文 Multitask_lea_001882(Multitask learning).pdf
        # font_size = page_text_lines[i][2]
        # if line_text in ['References', 'REFERENCES'] and font_size >= 11:
        if line_text in ['References', 'REFERENCES']:
            return True
    return False


def locate_reference_start_page(page_text_lines):
    ref_format = None
    is_reference_page = False
    font_size = 0.
    if not _search_reference_start(page_text_lines):
        return False, ref_format, font_size
    # 如果是 References 起始页，需要将数据预处理后再进一步检查 reference的格式。
    # 检查方法： 将 "References" 标记的下一行视作第一条 reference, 检查该reference格式作为这个References的格式，
    # 而 pdfminer 解析pdf文本并不是完全按从上到下顺序扫描，若不预处理，则可能 "References"标记的下一行并不是 实际位置上的下一行。
    # 样例见：2211.09117v2(MAGE- MAsked Generative Encoder to Unify Representation Learning and Image Synthesis).pdf，
    #       第9页为References起始页，pdfminer解析结果中"References"的下一行却是相隔遥远的右边顶行
    #       “Conference on Computer Vision (ICCV), pages 9640–9649, 2021.”
    # 因此进一步检查reference格式前，需将预处理将页面按分块排列。
    split_text_lines = split_page_to_blocks(page_text_lines)
    new_page_text_lines = split_text_lines[0]
    for text_lines in split_text_lines[1:]:
        new_page_text_lines = new_page_text_lines + text_lines

    for i in range(len(new_page_text_lines)):

        line_text = new_page_text_lines[i][1].strip()
        #print(f'DEBUG: {line_text}')
        font_size = new_page_text_lines[i][2]
        if not is_reference_page:
            if line_text in ['References', 'REFERENCES']:
                is_reference_page = True
            continue
        pat = r'\[(?P<ref_no>\d*)\] [\s\S]*'
        m = re.match(pat, line_text)
        if m:
            ref_format = RefFormat.REF_NO
            break
        pat = r'\[(?P<ref_id>\S*)\] [\s\S]*'
        m = re.match(pat, line_text)
        if m:
            ref_format = RefFormat.REF_ID
            break
        pat = r'(?P<ref_no>\d*)\. [\s\S]*'
        m = re.match(pat, line_text)
        if m:
            ref_format = RefFormat.REF_NUM_DOT
            break
        ref_format = RefFormat.REF_INDENT
        break


    return is_reference_page, ref_format, font_size


def check_reference(page_text_lines, ref_format, ref_font_size, probe_lines=10):
    if ref_format == RefFormat.REF_NO:
        return _check_reference_by_no(page_text_lines, ref_font_size, probe_lines)
    elif ref_format == RefFormat.REF_ID:
        return _check_reference_by_id(page_text_lines, ref_font_size, probe_lines)
    elif ref_format == RefFormat.REF_NUM_DOT:
        return _check_reference_by_num_dot(page_text_lines, ref_font_size, probe_lines)
    else:
        return _check_reference_by_indent(page_text_lines, ref_font_size, probe_lines)


def _extract_unformat_refs(arranged_text_lines):
    refs = []
    cur_ref = []
    ref_no = 0
    references_start = False
    ref_start_x = -1
    for _text_lines in arranged_text_lines:
        if references_start:
            ref_start_x = min([rect[1] for rect, _, _, _ in _text_lines])
        prev_y1, prev_y0 = -1, -1
        for _text_line in _text_lines:
            line_text = _text_line[1].strip()
            font_size = _text_line[2]
            if not references_start:
                if line_text in ['References', 'REFERENCES']:
                    references_start = True
                continue
            if not cur_ref:
                ref_start_x = _text_line[0][1]
            cur_y1, cur_x0, cur_y0, _ = _text_line[0]
            # 无缩进，可能是reference首行
            if cur_x0 - ref_start_x < 4:
                if cur_ref:
                    ref_no += 1
                    refs.append((ref_no, ' '.join(cur_ref).replace('- ', '')))
                    cur_ref = []
                # 删除原首行检测条件 (prev_y0 - cur_y1 > 5), 样例：Multitask_lea_001882(Multitask learning).pdf reference间行距只有2.15
                # if (prev_y0 < 0) or (prev_y0 - cur_y1 > 5) and (prev_y0 - cur_y1 < 15):
                if (prev_y0 < 0) or (prev_y0 - cur_y1 < 15):
                    cur_ref = [line_text]
                    ref_start_x = cur_x0
                # 不满足reference首行格式，Reference结束
                else:
                    break
            # 有缩进，且与首行行距紧凑，为reference续行
            elif (prev_y0 < 0) or (prev_y0 - cur_y1 < 4):
                cur_ref.append(line_text)
            else:
                break
            prev_y1, prev_y0 = cur_y1, cur_y0
    if cur_ref:
        ref_no += 1
        refs.append((ref_no, ' '.join(cur_ref).replace('- ', '')))
    return refs


def extract_refs(arranged_text_lines, ref_format):
    refs = []
    # pattern for RefFormat.REF_NO,
    pat1 = r'\[(?P<ref_no>\d*)\] [\s\S]*'
    # pattern for RefFormat.REF_ID,
    pat2 = r'\[(?P<ref_id>\S*)\] [\s\S]*'
    # pattern for RefFormat.REF_NUM_DOT
    pat3 = r'(?P<ref_no>\d*)\. [\s\S]*'
    cur_ref = []
    ref_no = 0
    for _text_lines in arranged_text_lines:
        for _text_line in _text_lines:
            line = _text_line[1].strip()
            if ref_format == RefFormat.REF_NO:
                m1 = re.match(pat1, line)
                if m1:
                    if cur_ref:
                        refs.append((ref_no, ' '.join(cur_ref).replace('- ', '')))
                    ref_no = int(m1.group('ref_no'))
                    cur_ref = [line]
                    continue
            elif ref_format == RefFormat.REF_ID:
                m2 = re.match(pat2, line)
                if m2:
                    if cur_ref:
                        refs.append((ref_no, ' '.join(cur_ref).replace('- ', '')))
                    ref_no += 1
                    cur_ref = [line]
                    continue
            elif ref_format == RefFormat.REF_NUM_DOT:
                m3 = re.match(pat3, line)
                if m3:
                    if cur_ref:
                        refs.append((ref_no, ' '.join(cur_ref).replace('- ', '')))
                    ref_no = int(m3.group('ref_no'))
                    cur_ref = [line]
                    continue
            if cur_ref:
                cur_ref.append(line)
    if cur_ref:
        refs.append((ref_no, ' '.join(cur_ref).replace('- ', '')))
    return refs


def parse_pdf(pdf_path):
    # 保存每页中的文本详情
    pdf_pages = []
    page_min_y = DEFAULT_MIN_Y
    page_max_y = DEFAULT_MAX_Y
    # 从PDF中提取页面
    for _page_no, page in enumerate(extract_pages(pdf_path)):
        # 初始化从页面中提取文本所需的变量
        page_text = []
        page_lines = []
        page_content = []
        horizontal_lines = []
        # 找到所有的元素
        page_elements = [element for element in page._objs]

        # first_page_max_y1 = 0
        # 查找组成页面的元素
        for i, element in enumerate(page_elements):
            #FOR DEBUG
            # if i == 0:
            #     print(f'DEBUG: page_no={_page_no}, y1={element.y1} {element.get_text()}')
            # 只处理文本元素
            if isinstance(element, LTTextContainer):
                # 提取每个文本元素的文本（去噪）
                lines = text_extraction(element, min_y=page_min_y, max_y=page_max_y)
                if lines is not None:
                    page_lines.extend(lines)
                    for _pos, _text, _font_size in lines:
                        # 显示格式的文本详情
                        page_text.append(f'{_page_no}/{_pos}/{_font_size}: {_text}')
                        # 显示格式的纯文本内容
                        page_content.append(_text)
            elif isinstance(element, LTLine):
                pos = (element.y1, element.x0, element.y0, element.x1)
                if abs(pos[0] - pos[2])<=1:
                    horizontal_lines.append(pos)
            # if _page_no == 0:
            #     first_page_max_y1 = max(first_page_max_y1, element.y1)
        # if _page_no == 0:
        #     page_max_y = min(first_page_max_y1 + 8, page_max_y)
        # 保存该页文本详情
        pdf_pages.append([page_text, page_lines, horizontal_lines])
        # print(f'DEBUG: {page_lines[0][1]}')
        # if _page_no == 0:
        #     min_y0 = DEFAULT_MAX_Y
        #     for pos, _, _ in page_lines:
        #         if pos[2] < min_y0:
        #             min_y0 = pos[2]
        #     page_min_y = min_y0 if min_y0 > DEFAULT_MIN_Y else page_min_y
        #     #FOR DEBUG
        #     print(f'DEBUG: page no: {_page_no}, page_min_y={page_min_y}, page_max_y={page_max_y}')
    return pdf_pages


def parse_refs(pdf_pages):
    refs_text_lines = []
    reference_start = False
    ref_format = None
    ref_font_size = 0
    is_reference = False
    header_y, footer_y = get_header_footer_y(pdf_pages)
    ref_page_no_list = []
    for page_no in range(len(pdf_pages)):
        text_lines = strip_header_footer(pdf_pages[page_no][1], header_y, footer_y)
        if not reference_start:
            reference_start, ref_format, ref_font_size = locate_reference_start_page(text_lines)
            is_reference = reference_start
            if reference_start:
                log(f'References start page {page_no+1}, format={ref_format}')
        else:
            is_reference = check_reference(text_lines, ref_format, ref_font_size)
        if is_reference:
            ref_page_no_list.append(page_no+1)
            page_text_lines = text_lines   # 基于预处理后的pdf_page来处理，而不用原来df_pages[page_no][1]
            split_text_lines = split_page_to_blocks(page_text_lines)
            for text_lines in split_text_lines:
                rearrange(text_lines)
            refs_text_lines.extend(split_text_lines)
        elif reference_start:
            break
    log(f'References pages are {ref_page_no_list}')
    if ref_format in [RefFormat.REF_NO, RefFormat.REF_ID, RefFormat.REF_NUM_DOT]:
        return extract_refs(refs_text_lines, ref_format)
    else:
        return _extract_unformat_refs(refs_text_lines)
