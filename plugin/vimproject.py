#!/usr/bin/env python
# -*- coding: utf-8 -*-

import vim
import os
import sys
import shutil
import hashlib
from pathlib import Path
import tempfile
from subprocess import call, Popen
from copy import copy
import vimrecoding

IS_WIN = int(vim.eval('has("win32")'))

#对于不同编译器的不同错误信息格式，第一项为错误，第二项为警告
_COMPILER_EFM = {
    'msvc' : [
        #error
        [
            r"%f(%l)%\s%#: %trror C%n: %m",
            r"%f(%l)%\s%#: fatal %trror C%n: %m",
            r"%s: fatal %trror LNK%n: %m",
            r"%s: %trror LNK%n: %m",
        ],
        #warning
        [
            r"%f(%l)%\s%#: %tarning C%n: %m",
            r"%s: %tarning LNK%n: %m",
        ],
    ],
    'llvm': [
        [
            r"%f(%l\,%c):  %trror: %m",
            r"%f: %\(undefined%.%#%\)%\@=%m",
        ],

        [
            r"%f(%l\,%c):  %tarning: %m",
        ],

    ],
    'gcc' : [
        [
            r"%f:%l:%c: %trror:%m",
            r"%f:%l:%c: fatal %trror:%m",
            r"%f:%l: %\(undefined%.%#%\)%\@=%m",
            r"%s:%f:%*[^:]: %\(undefined%.%#%\)%\@=%m",
        ],
        [
            r"%f:%l:%c: %tarning:%m",
        ],
    ],
    'mips-gcc': [
        [
            r"%f:%l: %trror:%m",
            r"%f:%l: fatal %trror:%m",
            r"%f:%l: %\(undefined%.%#%\)%\@=%m",
            r"%s:%f:%*[^:]: %\(undefined%.%#%\)%\@=%m",
        ],
        [
            r"%f:%l: %tarning:%m",
        ],
    ],
    'mdk' :[
        [
            r'''%trror:%s''',
            r'''%E"%f"\,%\s%#line%\s%#%l:%\s%#Error:%m''',
            r'''%-Z  %p^''', #mdk的信息缩进了2个空格
            r'''%-C%.%#''',
        ],
        [
            r'''%W"%f"\,%\s%#line%\s%#%l:%\s%#Warning:%m''',
        ],
    ],
    'ads' :[
        [
            r'''"%f"\,%\s%#line%\s%#%l:%\s%#%trror:%m''',
            r'''%trror:%s''',
        ],
        [
            r'''"%f"\,%\s%#line%\s%#%l:%\s%#%tarning:%m''',
        ],
    ],
    'avr' :[
        [
            r'''%trror[%s]:%m''',
            r'''%E"%f"\,%l%\s%#%trror%m''', #avr的列信息在文件信息之前，无法得到
            r'''%+C%[^ ]%#''',
            r'''%-Z%\s%#''',
        ],
        [
            r'''%W"%f"\,%l%\s%#%tarning%m''',
        ],
    ],
    'javac' : [
        [
            r"%E%f:%l: 错误: %m",
            r"%E%f:%l: error: %m",
            r"%-Z%p^",
            r"%-C%.%#",
        ],
        [
            r"%W%f:%l: 警告: %m",
            r"%W%f:%l: warning: %m",
        ],
    ],
    'common' : [
        [
            r"%f:%l:%m",
            r"%f:%l:%c:%m",
        ],
        [ ],
    ],
    'pclint' : [
        [
            r"%f(%l): %trror %n:%m",
        ],
        [
            r"%f(%l): %tarning %n:%m",
        ]
        ,
    ],
    'pylint' : [
        [
            r"%f:%l: %\([%[EF]%.%#%\)%\@=%m",
        ],
        [
            r"%f:%l: %\([%[WR]%.%#%\)%\@=%m",
        ]
    ],
    'scons' : [
        [
            r"%\(scons: building terminated because of errors.%\)%\@=%m",
        ],
        [],
    ],

    'lex' : [
        [
            r"%f:%l: %trror\,%m",
        ],
        [
            r"%f:%l: %tarning\,%m",
        ],
    ],

    'yacc' :[
        [
            r"%f:%l.%c-%\d%\+: %m",
        ],
        [
            r"%f:%l.%c-%\d%\+: %\(warning:%.%#%\)%\@=%m",
        ],
    ],
}


def formpath(p):
    return p.replace('\\', '/')

def str2vimfmt(s):
    ret = []
    for c in s:
        if c in ['\\', ' ', '|', '"', ',']:
            ret.append('\\')
        ret.append(c)
    return ''.join(ret)

def escape_text(text):
    if IS_WIN:
        return text
    else:
        return text.replace("\\", "\\\\")


class VimProject(object):
    def __init__(self):
        self.reset_config()
        self.commit_settings()

    def reset_config(self):
        ext = vim.eval('''expand('%:e')''')
        if not ext:
            ext = ''
        self.projectname = vim.eval('expand("%:t")')
        if not self.projectname:
            self.projectname = "untitled"
        self.basedir = formpath(vim.eval('getcwd()'))
        self.path = ['.']
        self.suffix = ['.' + ext]
        self.make= ''
        self.execute = ''
        self.files = []
        self.compiler = []
        self.type = ''
        self.warning = False
        self.pause = 0
        self.libtags = 0
        self.tags = []
        self.projectfile = ""
        self.vimcmd = ""

        if ext in ['py', 'pyw']:
            self.make = 'pylint -r n -f parseable %:p'
            self.compiler = ['pylint']

    def from_file(self, fname):
        fpproj = Path(fname).absolute()
        if not fname or not fpproj.is_file():
            return
        gl = {}
        try:
            exec(compile(fpproj.read_text(), fname, 'exec'), gl)
        except Exception as e:
            print(str(e), file=sys.stderr)
            return
        self.reset_config()
        self.projectfile = fpproj
        self.projectname = fpproj.stem
        self.basedir = formpath(str(fpproj.parent))
        if 'NAME' in gl:
            self.projectname = gl['NAME']
        if 'PATH' in gl:
            self.path = gl['PATH']
        if 'EXECUTE' in gl:
            self.execute = gl['EXECUTE']
        if 'TYPE' in gl:
            self.type = gl['TYPE']
        if 'SUFFIX' in gl:
            self.suffix = [s.lower() for s in gl['SUFFIX']]
        else:
            if self.type == 'python':
                self.suffix = ['.py', '.pyw']
            elif self.type == 'c':
                self.suffix = ['.c', '.h']
            elif self.type == 'cpp':
                self.suffix = ['.c', '.h', '.cpp', '.cc', '.cxx', '.hpp', '.hxx', '.hh']
            elif self.type == 'java':
                self.suffix = ['.java']
            elif self.type == 'latex':
                self.suffix = ['.tex']
            elif self.type == 'vim':
                self.suffix = ['.vim']
        if 'MAKE' in gl:
            self.make= gl['MAKE']
        if 'COMPILER' in gl:
            self.compiler = gl['COMPILER']
        else:
            self.compiler = ['common']
        if 'PAUSE' in gl:
            self.pause = gl['PAUSE']
        if 'LIBTAGS' in gl:
            self.libtags = gl['LIBTAGS']
        if 'TAGS' in gl:
            # self.tags = list(map(formpath, list(map(path.abspath, gl['TAGS']))))
            self.tags = [Path(p).absolute().as_posix() for p in gl['TAGS']]
        if 'VIMCMD' in gl:
            self.vimcmd = gl['VIMCMD']
        self.commit_settings()

    def get_temp_dir(self):
        if not self.tempdir.exists():
            self.tempdir.mkdir()
        return self.tempdir

    def get_fname_base(self):
        return str(self.get_temp_dir() / self.projectname)

    def get_file_list(self):
        return self.get_fname_base() + ".list.tmp"

    def get_tags_fname(self):
        return self.get_fname_base() + '.tags.tmp'

    def get_cscope_fname(self):
        return self.get_fname_base() + '.cscope.tmp'

    def get_make_tmpfile(self):
        return self.get_fname_base() + '.make.tmp'

    def get_grep_tmpfile(self):
        return self.get_fname_base() + '.grep.tmp'

    def get_session_fname(self):
        return self.get_fname_base() + '.session.tmp'

    def add_library_tags(self):
        if not self.libtags:
            return
        ret = []
        if self.type in ['c']:
            inc = os.environ.get("C_INCLUDE_PATH", None)
            if inc:
                ret += list(map(formpath, inc.split(os.pathsep)))
        elif self.type in ['cpp']:
            inc = os.environ.get("CPLUS_INCLUDE_PATH", None)
            if inc:
                ret += list(map(formpath, inc.split(os.pathsep)))
        for dir in ret:
            vim.command('silent set tags+=%s/tags' % str2vimfmt(dir))

    def add_cscope_database(self):
        if self.type in ['c', 'cpp', 'java']:
            vim.command('silent! cs add %s %s' % (str2vimfmt(self.get_cscope_fname()), str2vimfmt(self.basedir)))

    def load_session_file(self):
        session = self.get_session_fname()
        if self.projectfile and Path(session).is_file():
            vim.command(r'''silent so %s''' % str2vimfmt(session))

    def write_session_file(self):
        if self.projectfile:
            session_fname = self.get_session_fname()
            vim.command(r'''silent mks! %s''' % str2vimfmt(session_fname))

    def commit_settings(self):
        self.tempdir = Path(tempfile.gettempdir()) / ("vimproject_" + hashlib.md5(self.basedir.encode("utf-8")).hexdigest()[:10])
        vim.command('''silent set path=.,%s''' % (','.join([str2vimfmt(p if Path(p).is_absolute() else str(Path(self.basedir + '/' + p).absolute())) for p in self.path])))
        vim.command('silent set tags=%s' % ','.join(map(str2vimfmt, [self.get_tags_fname()] + self.tags)))
        self.add_library_tags()
        self.add_cscope_database()
        if self.vimcmd:
            vim.command(self.vimcmd)

    def open_quickfix(self):
        vim.command("execute 'copen 15'")
        if not self.is_error_in_quickfix():
            vim.command("execute 'normal G'")
        vim.command('wincmd p')
        vim.command('silent! lcd ' + str2vimfmt(self.basedir))

    def async_run(self, cmd, qffile=None):
        vim_cmd = 'silent !cd "{basedir}" && {cmd} 2>&1'.format(
            basedir = self.basedir,
            cmd=cmd
            )

        if qffile:
            vim_cmd += ' | tee "{qffile}"'.format(qffile=qffile)

        vim.command(vim_cmd)

        if qffile:
            enc = vim.eval("&encoding")
            vimrecoding.recode_file(qffile, enc)
            self.load_quickfix_file(qffile)

    def is_error_in_quickfix(self):
        qflist = vim.eval("getqflist()")
        for info in qflist:
            if int(info['valid']) != 0:
                # 有错误
                return 1
        return 0


    def make_project(self, args):
        self.update_compiler_efm()
        if self.make:
            make = self.make.replace("%:p", vim.eval('expand("%:p")'))
            self.async_run(make + " " + args, self.get_make_tmpfile())
        else:
            print("MAKE command is not set.", file=sys.stderr)

    def update_compiler_efm(self):
        fmts = []
        if not self.compiler:
            self.compiler = ['common']
        for compiler in self.compiler:
            if compiler in _COMPILER_EFM:
                if self.warning:
                    fmts += _COMPILER_EFM[compiler][1]
                fmts += _COMPILER_EFM[compiler][0]
            else:
                vim.command("silent compiler %s" % compiler)
                break
        vim.command(r"silent set efm=%s" % ','.join(map(str2vimfmt, fmts)))

    def grep_text(self, regex):
        regex = escape_text(regex)
        self.refresh_files()
        file_list = self.get_file_list()
        if not os.path.exists(file_list):
            print("%s not exist." % file_list, file=sys.stderr)
            return
        grepcmd = r'cat {listfile} | pyargs pygrep -HnCS "{regex}"'.format(
            listfile=file_list,
            regex=regex,
            )
        self.set_grep_efm()
        self.async_run(grepcmd, self.get_grep_tmpfile())

    def set_grep_efm(self):
        vim.command(r"silent set efm=%f:%l:%c:%m,%f:%l:%m")

    def replace_pattern(self, pattern, repl):
        pattern = escape_text(pattern)
        repl = escape_text(repl)
        self.refresh_files()
        flist = self.get_file_list()
        if Path(flist).is_file():
            self.async_run('cat "{flist}" | pyargs pyrep -i -f "{pattern}" -t "{repl}"'.format(
                flist=flist,
                pattern=pattern,
                repl=repl
                ))
        else:
            print("%s not found!" % flist, file=sys.stderr)

    def load_quickfix_file(self, fname):
        cwd = formpath(vim.eval('getcwd()'))
        vim.command('silent cd ' + str2vimfmt(self.basedir))
        vim.command('silent cfile %s' % str2vimfmt(fname))
        vim.command('silent cd ' + str2vimfmt(cwd))
        self.open_quickfix()

    def load_make_result(self):
        if Path(self.get_make_tmpfile()).is_file():
            self.update_compiler_efm()
            self.load_quickfix_file(self.get_make_tmpfile())
        else:
            print("%s not exist." % self.get_make_tmpfile(), file=sys.stderr)

    def load_grep_result(self):
        if Path(self.get_grep_tmpfile()).is_file():
            self.set_grep_efm()
            self.load_quickfix_file(self.get_grep_tmpfile())
        else:
            print("%s not exist." % self.get_grep_tmpfile(), file=sys.stderr)

    def invert_warning(self):
        self.warning = not self.warning
        self.load_make_result()

    def search_files(self):
        basedir = Path(self.basedir)
        for ptn in self.path:
            for suffix in self.suffix:
                yield from basedir.glob(ptn + "/*" + suffix)

    def refresh_files(self):
        self.files = []
        with open(self.get_file_list(), 'w') as f:
            for fname in self.search_files():
                self.files.append(fname)
                print(fname, file=f)

    def refresh_tags(self):
        call(['ctags','--c-kinds=+px', '--c++-kinds=+px', '--fields=+iaS', '--extra=+q', '-L', self.get_file_list(), '-f', self.get_tags_fname()])

    def refresh_cscope(self):
        if self.type in ['c', 'cpp', 'java']:
            vim.command('silent! cs kill -1')
            call(['cscope', '-b', '-k', '-f', self.get_cscope_fname(), '-i', self.get_file_list()])
            self.add_cscope_database()

    def update(self):
        self.refresh_files()
        self.refresh_tags()
        self.refresh_cscope()
        print("update over.")

    def run_execute(self, args):
        if self.execute:
            execute = self.execute #.replace('/', '\\')
            origdir = formpath(vim.eval('getcwd()'))
            vim.command('silent! lcd ' + str2vimfmt(self.basedir))
            os.system(execute + ' ' + args + (' && pause || pause' if self.pause else ''))
            vim.command('silent! lcd ' + str2vimfmt(origdir))
        else:
            if vim.eval('&ft') in ['python', 'perl', 'lua']:
                os.system(vim.eval('&ft') + ' ' + vim.eval('''expand('%:p')''') + ' ' + args + ' && pause || pause')
            else:
                print("no execute", file=sys.stderr)


try:
    g_vimproject = VimProject()
except Exception as e:
    import traceback
    print(traceback.format_exc())

def from_this_file():
    fname = vim.eval('''expand('%:p')''')
    g_vimproject.from_file(fname)

def update_project_history():
    if not g_vimproject.projectfile:
        return

    fname = str(g_vimproject.projectfile)
    if fname.endswith(".vprj"):
        fs = []
        histfile = vim.eval("$HOME") + "/.vimproject"
        if Path(histfile).is_file():
            fs = [l for l in [l.strip() for l in open(histfile, "r").readlines()] if l]
        try:
            if not IS_WIN:
                ret = fs.index(fname)
                fs.pop(ret)
            else:
                for i in range(len(fs)):
                    if fs[i].lower() == fname.lower():
                        fs.pop(i)
                        break
        except:
            pass
        if len(fs) > 29:
            fs = fs[:29]
        fs.insert(0, fname)
        with open(histfile, 'w') as f:
            f.writelines([l + '\n' for l in fs])

def select_history_project():
    histfile = vim.eval("$HOME") + "/.vimproject"
    if Path(histfile).is_file():
        fs = [l for l in [l.strip() for l in open(histfile, "r").readlines()] if l]
        if fs:
            ret = int(vim.eval('''inputlist(['Project history list here, select one:', %s])''' % ', '.join(['"%2d: %s. %s"' % (i + 1, (Path(fs[i]).name + ' ').ljust(30, '.'), str(Path(fs[i]).parent)) for i in range(len(fs))])))
            if 0 < ret <= len(fs):
                vim.command('silent edit %s' % str2vimfmt(fs[ret - 1]))
        else:
            print("no project history")
    else:
        print("no project history")


def edit_project_file():
    if g_vimproject.projectfile:
        vim.command('silent find %s' % str2vimfmt(str(g_vimproject.projectfile)))
        return
    print("Project file does not exist, cannot open it!", file=sys.stderr)

def edit_file_list_file():
    fname = g_vimproject.get_file_list()
    if Path(fname).is_file():
        vim.command('silent find %s' % str2vimfmt(fname))
    else:
        print("File list file does not exist, cannot open it!", file=sys.stderr)

def search_project_file():
    files = []
    cwd = formpath(vim.eval('getcwd()'))
    while 1:
        ret = os.listdir(cwd)
        for fname in ret:
            if fname.lower().endswith('.vprj'):
                files.append(cwd + '/' + fname)
            elif fname.lower().endswith('.jvprj'):
                files.append(cwd + '/' + fname)
        _cwd = str(Path(cwd).parent)
        if _cwd == cwd:
            break
        else:
            cwd = _cwd
    if files:
        ret = int(vim.eval('''inputlist(['Projects found, select one:', %s])''' % ', '.join(['"%2d: %s. %s"' % (i+1, Path(files[i]).name + ' '.ljust(30, '.'), str(Path(files[i]).parent)) for i in range(len(files))])))
        if 0 < ret <= len(files):
            vim.command('silent edit %s' % str2vimfmt(files[ret - 1]))
    else:
        print("Have not found any project file.", file=sys.stderr)

def start_terminal_on_project():
    if IS_WIN:
        import platform

        if int(platform.win32_ver()[0]) >= 10:
            Popen("start cmd.exe /c cmdex.exe", cwd=g_vimproject.basedir, shell=1)
        else:
            Popen("start Console.exe -t cmdex", cwd=g_vimproject.basedir, shell=1)

    else:
        Popen("gnome-terminal --working-directory '%s'" % g_vimproject.basedir, shell = 1)

def make_this_file(args):
    target = vim.eval("expand('%')")
    g_vimproject.make_project(target + " " + args)

def to_re_pattern(s):
    ss = []
    for c in s:
        if c in r"\[]{}().*?+":
            ss.append("\\")
            ss.append(c)
        elif c == "\n":
            ss.append('\\n')
        else:
            ss.append(c)
    return ''.join(ss)

def grep_selection():
    selection = vim.eval("VPGetVisual()")
    if not selection:
        return
    g_vimproject.grep_text(to_re_pattern(selection))

def replace_to(pattern):
    ret = vim.eval('input("Input replacement: ")')
    do = vim.eval('''input('Do you want to replace "%s" to "%s"?(y/n)')''' % (pattern, ret))
    if do and do.lower() in ['y', 'yes']:
        g_vimproject.replace_pattern(pattern, ret)

def replace_input():
    pattern = vim.eval('input("Input pattern: ")')
    if not pattern:
        return
    replace_to(pattern)

def replace_this_word():
    word = vim.eval('expand("<cword>")')
    if not word:
        return
    replace_to("".join(["\\b", word, "\\b"]))

def replace_selection():
    sel = vim.eval('VPGetVisual()')
    replace_to(to_re_pattern(sel))

