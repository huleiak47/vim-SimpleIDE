#!/usr/bin/env python
# -*- coding:utf-8 -*-


import os
import sys
import chardet


def guess_encoding(line):
    encs = ["ascii", "utf-8", "cp936", "big5", "latin1"]
    for enc in encs:
        try:
            new_line = line.decode(enc, "strict")
            return enc, new_line
        except UnicodeError:
            pass

    ret = chardet.detect(line)
    enc = ret[0]
    new_line = line.decode(enc, "replace")
    return enc, new_line

def recode_std(enc):
    while 1:
        line = sys.stdin.readline()
        if not line:
            break
        src_enc, new_line = guess_encoding(line)

        sys.stdout.write(new_line.encode(enc, "replace"))
        sys.stdout.flush()

def recode_file(fname, enc):
    text = open(fname, "rb").read().replace(b'\r', b'')
    src_enc, new_text = guess_encoding(text)

    with open(fname, "wb") as f:
        f.write(new_text.encode(enc, "replace"))
