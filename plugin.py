from nubia import PluginInterface, CompletionDataSource
from nubia import context
from nubia import exceptions
from nubia import eventbus

class NubiaExampleContext(context.Context):

    # def __init__(self):
    #     super().__init__(self)

    def on_connected(self, *args, **kwargs):
        pass

    def on_cli(self, cmd, args):
        # dispatch the on connected message
        self.verbose = args.verbose
        self.registry.dispatch_message(eventbus.Message.CONNECTED)

    def on_interactive(self, args):
        self.verbose = args.verbose
        ret = self._registry.find_command("connect").run_cli(args)
        if ret:
            raise exceptions.CommandError("Failed starting interactive mode")
        # dispatch the on connected message
        self.registry.dispatch_message(eventbus.Message.CONNECTED)


class ZoteroPlugin(PluginInterface):

    def create_context(self):
        # pass
        return NubiaExampleContext()

    def validate_args(self, args):
        pass

    # def get_opts_parser(self, add_help=True):
    #     pass

#     def get_completion_datasource_for_global_argument(self, argument):
#         if argument == "--config":
#             return ConfigFileCompletionDataSource()
#         return None
#
# class ConfigFileCompletionDataSource(CompletionDataSource):
#     def get_all(self):
#         return ["/tmp/c1", "/tmp/c2"]
