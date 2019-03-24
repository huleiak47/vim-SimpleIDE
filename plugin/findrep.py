#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
import re
from pathlib import Path


def find_pattern(files: list, pattern: str, enc):
    ptn = re.compile(pattern.encode(enc))
    for fname in files:
        try:
            with open(fname, 'rb') as fp:
                for i, line in enumerate(fp):
                    for mobj in ptn.finditer(line):
                        yield "{0}:{1}:{2}:{3}".format(
                            str(fname), i + 1,
                            mobj.start() + 1,
                            line.rstrip().decode(enc))
        except (IOError, FileExistsError, UnicodeError):
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
            print("file: %s" % fname, file=sys.stderr)


def replace_pattern(files: list, pattern: str, to: str, enc):
    ptn_from = re.compile(pattern.encode(enc))
    ptn_to = to.encode(enc)
    for fname in files:
        lines = []
        is_replaced = False
        try:
            with open(fname, 'rb') as fp:
                for i, line in enumerate(fp):
                    rep = ptn_from.sub(ptn_to, line)
                    if rep != line:
                        is_replaced = True
                        lines.append(rep)
                        yield "{0}:{1}:{2}".format(
                            str(fname), i + 1, line.rstrip().decode(enc))
                    else:
                        lines.append(line)

            if is_replaced:
                with open(fname, 'wb') as fp:
                    fp.writelines(lines)

        except (IOError, FileExistsError, UnicodeError):
            import traceback
            print(traceback.format_exc(), file=sys.stderr)
            print("file: %s" % fname, file=sys.stderr)
