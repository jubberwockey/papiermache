from prompt_toolkit import PromptSession
from prompt_toolkit.completion import NestedCompleter
from db import ZoteroDatabase
from dispatcher import Dispatcher


exit_cmds = ['exit', 'q', 'quit']
completion_json_template = {
    'show': {
        'version': None,
        # 'ip': {'interface': {'brief'}}
    },
    'find': None,
    'select': {},
    'add': {'pdf': {}},
    'exit': None,
    # 'enable': None,
}



s = PromptSession()
z = ZoteroDatabase(local=True)

autocomplete_dict = z.get_autocompletes()
db_completion_json = {v: None for v in autocomplete_dict.values()}
completion_json = dict(completion_json_template)
completion_json['select'] = db_completion_json
completion_json['add']['pdf'] = db_completion_json

completer = NestedCompleter.from_nested_dict(completion_json)

d = Dispatcher(db_handler=z, commands=completion_json)

while input not in exit_cmds:
    input = s.prompt('>', completer=completer)
    d.execute(input)
