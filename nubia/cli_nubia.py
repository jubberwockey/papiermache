## https://github.com/facebookincubator/python-nubia
import sys
from nubia import Nubia, Options
from plugin import ZoteroPlugin
import commands


plugin = ZoteroPlugin()
shell = Nubia(
    name="nubia_example",
    command_pkgs=commands,
    plugin=plugin,
    options=Options(persistent_history=False),
)
sys.exit(shell.run())
