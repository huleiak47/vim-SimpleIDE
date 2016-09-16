#!/usr/bin/env python
# -*- coding:utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division

import sys
import chardet

if len(sys.argv) > 1:
    dst_enc = sys.argv[1]
else:
    dst_enc = sys.argv[1]
src_enc = "ascii"

def guess_encoding(line):
    encs = ["utf-8", "cp936", "big5", "latin1"]
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

while 1:
    line = sys.stdin.readline()
    if not line:
        break
    try:
        new_line = line.decode(src_enc, "strict")
    except UnicodeError:
        src_enc, new_line = guess_encoding(line)

    sys.stdout.write(new_line.encode(dst_enc, "replace"))
    sys.stdout.flush()

