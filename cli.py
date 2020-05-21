from prompt_toolkit import PromptSession
from src.dispatcher import Dispatcher
import asyncio


async def main(disp):
    exit_cmds = disp.get_exit_commands()
    input = ''
    while input not in exit_cmds:
        input = await asyncio.wait_for(disp.session.prompt_async('>', completer=disp.get_completer()), timeout=120)
        disp.execute(input)

    disp.shutdown("Exiting...")


if __name__ == '__main__':
    disp = Dispatcher(session=PromptSession())
    try:
        asyncio.run(main(disp))
    except (KeyboardInterrupt, EOFError):
        disp.shutdown("Manual Interrupt, exiting...")
    except asyncio.TimeoutError:
        disp.shutdown("Timeout, shutting down...")
    # except Exception as e:
    #     disp.shutdown("An error occured, shutting down...\n{}".format(e))
    #     raise
