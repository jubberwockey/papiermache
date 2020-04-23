import sys
from prompt_toolkit import PromptSession
from utils.dispatcher import Dispatcher

s = PromptSession()
d = Dispatcher(session=s)

exit_cmds = d.get_exit_commands()

while input not in exit_cmds:
    try:
        input = s.prompt('>', completer=d.get_completer())
        d.execute(input)
    except (KeyboardInterrupt, EOFError):
        print("Manual Interrupt, exiting...")
        d.shutdown()
        sys.exit()

print("Exiting...")
d.shutdown()
sys.exit(0)
