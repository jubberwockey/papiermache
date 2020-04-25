import sys
from prompt_toolkit import PromptSession
from utils.dispatcher import Dispatcher
import asyncio


def shutdown(dispatcher, msg=''):
    print(msg)
    dispatcher.shutdown()
    sys.exit(0)

async def main():
    s = PromptSession()
    d = Dispatcher(session=s)

    exit_cmds = d.get_exit_commands()
    input = ''
    while input not in exit_cmds:
        try:
            input = await asyncio.wait_for(s.prompt_async('>', completer=d.get_completer()), timeout=60)
            d.execute(input)
        except (KeyboardInterrupt, EOFError):
            shutdown(d, "Manual Interrupt, exiting...")
        except asyncio.TimeoutError:
            shutdown(d, "Timeout, shutting down...")

    shutdown(d, "Exiting...")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # need to clean up here
        print("KeyboardInterrupt")
