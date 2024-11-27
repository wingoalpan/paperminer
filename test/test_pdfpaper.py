
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
import pdfpaper as pp


def test_merge_line():
    lines = [[3, 6]]
    segments=[(5, 8), (0, 2), (11, 14), (10, 12), (14, 15.5), (18, 20), (21, 22), (18, 22.5), (2, 7.8), (9, 23)]
    for x0, x1 in segments:
        pp._merge_line(x0, x1, lines)
        print(f'add ({x0}, {x1}), lines={lines}')


def test_slit_vertical():
    segments=[(5, 8), (0, 2), (11, 14), (10, 12), (14, 15.5), (18, 20), (21, 22), (18, 22.5), (2, 7.8), (9, 23)]
    rects = [(y1, 0, y0, 0) for y0, y1 in segments]
    lines = pp._slit_vertical(rects)
    print(lines)


def test_header_footer_alike():
    # 有页眉、页码, 首页有页眉 （Adversarial Feature Learning）
    #pdf_path = '../../papers/1605.09782v7(Adversarial Feature Learning).pdf'
    # 有页眉（无横线分开），无页码 （SCAN: Learning to Classify Images without Labels）
    #pdf_path = '../../papers/2005.12320v2(SCAN- Learning to Classify Images without Labels).pdf'
    # 无页眉，有页码，部分页有页底注释 （Large Scale Adversarial Representation Learning）
    #pdf_path = '../../papers/1907.02544v2(Large Scale Adversarial Representation Learning).pdf'
    # 无页眉，有页码，页码和内容间距小
    #pdf_path = '../../papers/2112.10752v2(High-Resolution Image Synthesis with Latent Diffusion Models).pdf'
    #pdf_path = '../../papers/2210.17323v2(GPTQ- Accurate Post-Training Quantization for Generative Pre-trained Transformers).pdf'
    #有页眉，横线分割， 无页脚，页码在页眉上
    #pdf_path = '../../papers/2102.09672v1(Improved Denoising Diffusion Probabilistic Models).pdf'
    #页眉只有横线，有页码
    #pdf_path = '../../papers/2106.09685v2(LoRA- Low-Rank Adaptation of Large Language Models).pdf'
    #无页眉有页码
    #pdf_path = '../../papers/1512.03385v1(Deep Residual Learning for Image Recognition).pdf'
    #无页眉有页码, 含补充材料
    #pdf_path = '../../papers/2307.08702v1(Diffusion Models Beat GANs on Image Classification).pdf'
    pdf_path = '../../papers/2010.09233v2(Auto-Encoding Variational Bayes for Inferring Topics and Visualization).pdf'
    #无页眉有页码
    pdf_path = '../../papers/2211.09117v2(MAGE- MAsked Generative Encoder to Unify Representation Learning and Image Synthesis).pdf'
    pdf_pages = pp.parse_pdf(pdf_path)
    header_y, footer_y = pp.get_header_footer_y(pdf_pages)
    for page_no in range(len(pdf_pages)):
        if page_no == 0:
            continue
        text_lines = pdf_pages[page_no][1]
        header, footer = pp.get_header_footer(text_lines, header_y, footer_y)
        print(f'page {page_no}: header={header}, footer={footer}')
        # horizontal_lines = pdf_pages[page_no][2]
        # h_line = horizontal_lines
        # print(f'page {page_no}: horizontal_lines={ pdf_pages[page_no][2]}')


def main():
    print('')
    test_header_footer_alike()


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


