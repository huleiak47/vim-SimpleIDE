"coding:utf-8
if has('g:vimproject_loaded')
    finish
endif
let g:vimproject_loaded = 1

let s:plugin_path = escape(expand('<sfile>:p:h'), '\')
"exe 'python sys.path = ["' . s:plugin_path . '"] + sys.path'

function! VPGetVisual() range
    let reg_save = getreg('"')
    let regtype_save = getregtype('"')
    let cb_save = &clipboard
    set clipboard&
    normal! ""gvy
    let selection = getreg('"')
    call setreg('"', reg_save, regtype_save)
    let &clipboard = cb_save
    return selection
endfunction

python3 << PYTHON_EOF
import sys
import vim
sys.path.append(vim.eval("s:plugin_path"))
from vimproject import *
PYTHON_EOF

au FileType vimproj             python3 from_this_file()
au FileType vimproj             python3 update_project_history()
au FileType vimproj             set syntax=python
au BufWritePost *.vprj,*.jvprj  python3 from_this_file()

au VimLeavePre *                python3 g_vimproject.write_session_file()

command! -nargs=* VPRunExecution    python3 g_vimproject.run_execute('''<args>''')
command! -nargs=* VPMakeProject     python3 g_vimproject.make_project('''<args>''')
command! -nargs=* VPMakeThisFile    python3 make_this_file('''<args>''')
command! VPUpdateTags               python3 g_vimproject.update()
command! VPInvertWarning            python3 g_vimproject.invert_warning()
command! VPEditProject              python3 edit_project_file()
command! VPEditFileListFile         python3 edit_file_list_file()
command! VPSearchProject            python3 search_project_file()
command! VPSelectHistProject        python3 select_history_project()
command! VPLoadMakeResult           python3 g_vimproject.load_make_result()
command! VPLoadGrepResult           python3 g_vimproject.load_grep_result()
command! VPStartTerminal            python3 start_terminal_on_project()
command! VPLoadSessionFile          python3 g_vimproject.load_session_file()

"greps
function! s:GrepThisWord()
    let word = expand('<cword>')
    if word != ''
        if &encoding != &termencoding
            let word = iconv(word, &encoding, &termencoding)
        endif
        execute 'python3 g_vimproject.grep_text("\\b' . expand('<cword>') . '\\b")'
    endif
endfunction

function! s:GrepPattern()
    let pattern = input('Grep: ')
    if pattern != ''
        if &encoding != &termencoding
            let pattern = iconv(pattern, &encoding, &termencoding)
        endif
        execute 'python3 g_vimproject.grep_text("' . pattern . '")'
    endif
endfunction

command! VPGrepThisWord         call s:GrepThisWord()
command! VPGrepInput            call s:GrepPattern()
command! VPGrepSelection        python3 grep_selection()
command! VPReplaceThisWord      python3 replace_this_word()
command! VPReplaceInput         python3 replace_input()
command! VPReplaceSelection     python3 replace_selection()
