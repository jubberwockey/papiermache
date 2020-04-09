import os
import warnings
from prompt_toolkit.completion import NestedCompleter
from utils.db import ZoteroDatabase
from utils.scihub import SciHub

class Dispatcher():

    def __init__(self, session, local=True):
        self.exit_cmds = ['exit', 'q', 'quit']
        self.cmd_template = {
            'show': {
                'version': None,
                # 'ip': {'interface': {'brief'}}
            },
            'find': None,
            'select': {},
            'add': {'pdf': {}},
        }
        self.cmd_template.update({c: None for c in self.exit_cmds})
        self.paper_dir = os.environ['PAPER_PATH']

        self.session = session
        self.db = ZoteroDatabase(local=local)
        self.scihub = SciHub(use_fallback=True)

        self.completions = None
        self.papers = None
        self.papers_reverse = None
        self.completer = self.build_completer()
        self.selected_key = None

    def build_completer(self):
        self.completions = dict(self.cmd_template)

        self.papers = self.db.get_autocompletes()
        self.papers_reverse = {v: k for k, v in self.papers.items()}
        paper_completions = {v: None for v in self.papers.values()}
        self.completions['select'] = paper_completions
        self.completions['add']['pdf'] = paper_completions

        return NestedCompleter.from_nested_dict(self.completions)

    def get_completer(self):
        return self.completer

    def get_exit_commands(self):
        return self.exit_cmds

    def shutdown(self):
        self.db.close_connection()
        return 0

    def verify_command(self, cmd_list):
        """checks if command follows structure of a valid command
        still very fishy, validates every word..."""
        def recursive_verify(cmd_list, commands):
            if len(cmd_list) > 0:
                cmd = cmd_list.pop(0)
                if commands is not None:
                    if cmd in commands:
                        return recursive_verify(cmd_list, commands[cmd])
                    else:
                        warnings.warn('input not valid: {}'.format(cmd))
                        return False
                # collides with free-form input:
                else:
                    warnings.warn('too many inputs: {}'.format(cmd))
                    return False
            else:
                if commands is not None:
                    warnings.warn('additional input missing')
                    return False
                else:
                    return True
        # recursive_verify manipulates list, therefore copy:
        cmd_list_copy = list(cmd_list)
        return recursive_verify(cmd_list_copy, self.completions)

    def execute(self, input):
        cmd = input.split()
        self.dispatch(cmd)
        # if self.verify_command(cmd) is True:
        #     self.dispatch(cmd)

    def dispatch(self, cmd_list):
        execute_cmd = cmd_list.pop(0)

        if execute_cmd == 'find':
            self.execute_find(cmd_list)
        elif execute_cmd == 'select':
            self.selected_key = self.execute_select(cmd_list)
        elif execute_cmd == 'add':
            execute_cmd = cmd_list.pop(0)
            if execute_cmd == 'pdf':
                self.execute_add_pdf(cmd_list)

    def execute_find(self, cmd_list):
        pass

    def execute_select(self, cmd_list):
        selected = ' '.join(cmd_list)
        selected_key = self.papers_reverse[selected]
        print('Selected:', selected_key)
        return selected_key

    def execute_add_pdf(self, cmd_list):
        if len(cmd_list) == 0:
            selected_key = self.selected_key
            print('Add for previously selected paper.'.format(self.papers[self.selected_key]))
        else:
            selected = ' '.join(cmd_list)
            selected_key = self.papers_reverse[selected]
            print('Add for selected paper.')

        attachments = self.db.get_attachments(selected_key)
        if len(attachments) > 0:
            print('Attachments already present')
            print(attachments)

        input = self.session.prompt('>>Are you sure? y/n: ')
        if input == 'y':
            item_data = self.db.get_item(selected_key)

            file_name = self.build_file_name(item_data)

            if 'DOI' in item_data:
                result = self.scihub.download(item_data['DOI'], path=self.paper_dir+file_name)
            elif 'url' in item_data:
                result = self.scihub.download(item_data['url'], path=self.paper_dir+file_name)
            else:
                print('No DOI/URL found, please provide:')
                url = self.session.prompt('>>')
                result = self.scihub.download(url, path=self.paper_dir+file_name)

            if 'err' in result:
                warnings.warn("Could not retrieve file. Attachment creation skipped.")
            else:
                created_key = self.db.create_attachment(file_name, selected_key)
                print('Created key', created_key)
                return created_key

    def build_file_name(self, item_dict):
        name = item_dict['creators'][0]['lastName']
        if len(item_dict['creators']) > 1:
             name += ' et al'

        year = item_dict['date'].split('-')[0]

        if 'shortTitle' in item_dict:
            title = item_dict['shortTitle'].split(':')[0]
        else:
            title = item_dict['title'].split(':')[0]

        return '_'.join([name, year, title]) + '.pdf'
