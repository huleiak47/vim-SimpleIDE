"coding:utf-8
if has('g:vimproject_loaded')
    finish
endif
let g:vimproject_loaded = 1

let s:plugin_path = escape(expand('<sfile>:p:h'), '\')
"exe 'python sys.path = ["' . s:plugin_path . '"] + sys.path'

function! VPGetVisual()
    " Why is this not a built-in Vim script function?!
    let [lnum1, col1] = getpos("'<")[1:2]
    let [lnum2, col2] = getpos("'>")[1:2]
    let lines = getline(lnum1, lnum2)
    let lines[-1] = lines[-1][: col2 - (&selection == 'inclusive' ? 0 : 1)]
    let lines[0] = lines[0][col1 - 1:]
    return join(lines, "\n")
endfunction

python << PYTHON_EOF
import sys
import vim
sys.path.append(vim.eval("s:plugin_path"))
from vimproject import *
PYTHON_EOF

au FileType vimproj             python from_this_file()
au FileType vimproj             python update_project_history()
au FileType vimproj             set syntax=python
au BufWritePost *.vprj,*.jvprj  python from_this_file()

au VimLeavePre *                python g_vimproject.write_session_file()

command! -nargs=* VPRunExecution    python g_vimproject.run_execute('''<args>''')
command! -nargs=* VPMakeProject     python g_vimproject.make_project('''<args>''')
command! -nargs=* VPMakeThisFile    python make_this_file('''<args>''')
command! VPUpdateTags               python g_vimproject.update()
command! VPInvertWarning            python g_vimproject.invert_warning()
command! VPEditProject              python edit_project_file()
command! VPEditFileListFile         python edit_file_list_file()
command! VPSearchProject            python search_project_file()
command! VPSelectHistProject        python select_history_project()
command! VPLoadMakeResult           python g_vimproject.load_make_result()
command! VPLoadGrepResult           python g_vimproject.load_grep_result()
command! VPStartTerminal            python start_terminal_on_project()
command! VPLoadSessionFile          python g_vimproject.load_session_file()

"greps
function! s:GrepThisWord()
    let word = expand('<cword>')
    if word != ''
        if &encoding != &termencoding
            let word = iconv(word, &encoding, &termencoding)
        endif
        execute 'python g_vimproject.grep_text("\\b' . expand('<cword>') . '\\b")'
    endif
endfunction

function! s:GrepPattern()
    let pattern = input('Grep: ')
    if pattern != ''
        if &encoding != &termencoding
            let pattern = iconv(pattern, &encoding, &termencoding)
        endif
        execute 'python g_vimproject.grep_text("' . pattern . '")'
    endif
endfunction

command! VPGrepThisWord         call s:GrepThisWord()
command! VPGrepInput            call s:GrepPattern()
command! VPGrepSelection        python grep_selection()
command! VPReplaceThisWord      python replace_this_word()
command! VPReplaceInput         python replace_input()
command! VPReplaceSelection     python replace_selection()
