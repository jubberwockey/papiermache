from prompt_toolkit import PromptSession
from utils.dispatcher import Dispatcher

s = PromptSession()
d = Dispatcher(session=s)

exit_cmds = d.get_exit_commands()

while input not in exit_cmds:
    input = s.prompt('>', completer=d.get_completer())
    d.execute(input)

d.shutdown()
