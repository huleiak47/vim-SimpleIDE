"coding:utf-8
if has('g:vimproject_loaded')
    finish
endif
let g:vimproject_loaded = 1

let s:plugin_path = escape(expand('<sfile>:p:h'), '\')
"exe 'python sys.path = ["' . s:plugin_path . '"] + sys.path'

python << PYTHON_EOF
import sys
import vim
sys.path.append(vim.eval("s:plugin_path"))
from vimproject import *
PYTHON_EOF

au FileType vimproj py from_this_file()
au FileType vimproj py update_project_history()
au FileType vimproj set syntax=python
au BufWritePost *.vprj py from_this_file()

au QuickFixCmdPre * py before_quickfix_cmd()
au QuickFixCmdPost * py after_quickfix_cmd()

au VimLeavePre * py g_vimproject.write_session_file()

command -nargs=* Run py g_vimproject.run_execute('''<args>''')
command UpdateTags py g_vimproject.update()
command InvertWarning py g_vimproject.invert_warning()
command EditProject py edit_project_file()
command EditFileListFile py edit_file_list_file()
command SearchProject py search_project_file()
command SelectHistProject py select_history_project()
command LoadMakeResult py g_vimproject.load_make_result()
command LoadGrepResult py g_vimproject.load_grep_result()
command StartTerminal py start_terminal_on_project()
command LoadSessionFile py g_vimproject.load_session_file()
command MakeThisFile py make_this_file()

