import os
import warnings
from prompt_toolkit.completion import NestedCompleter
from lisc.requester import Requester
from lisc.urls.open_citations import OpenCitations
from utils.db import ZoteroDatabase
from utils.scihub import SciHub


class Dispatcher():

    def __init__(self, session, local=True):
        self.exit_cmds = ['exit', 'q', 'quit']
        self.cmd_template = {
            'find': None,
            'select': {
                'all': None,
                'none': None,
                'collection': None,
                'tag': None,
                },
            'backup': None,
            'add': {
                'pdf': {
                    'all': None,
                    'none': None,
                    'collection': None,
                    'tag': None,
                    },
                'relations': {
                    'all': None,
                    'none': None,
                    'collection': None,
                    'tag': None,
                    },
                },
            }
        self.cmd_template.update({c: None for c in self.exit_cmds})
        self.paper_dir = os.environ['PAPER_PATH']

        self.session = session
        self.db = ZoteroDatabase(local=local)

        self.completions = None
        self.papers = None
        self.papers_reverse = None
        self.completer = self.build_completer()
        self.selected_keys = None

    def build_completer(self):
        self.completions = dict(self.cmd_template)

        self.papers = self.db.get_autocompletes()
        self.papers_reverse = {v: k for k, v in self.papers.items()}
        paper_completions = {v: None for v in self.papers.values()}
        self.completions['select'].update(paper_completions)
        self.completions['add']['pdf'].update(paper_completions)
        self.completions['add']['relations'].update(paper_completions)

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
        if len(cmd) > 0:
            self.dispatch(cmd)
        # if self.verify_command(cmd) is True:
        #     self.dispatch(cmd)

    def dispatch(self, cmd_list):
        execute_cmd = cmd_list.pop(0)

        if execute_cmd == 'find':
            self.execute_find(cmd_list)
        elif execute_cmd == 'select':
            self.selected_keys = self.execute_select(cmd_list)
        elif execute_cmd == 'add':
            execute_cmd = cmd_list.pop(0)
            if execute_cmd == 'pdf':
                self.execute_add_pdf(cmd_list)
            if execute_cmd == 'relations':
                self.execute_add_relations(cmd_list)

    def execute_find(self, cmd_list):
        pass

    def execute_select(self, cmd_list):
        return self.select_keys(cmd_list)

    def execute_add_relations(self, cmd_list):
        if len(cmd_list) == 0:
            selected_keys = self.selected_keys
        else:
            selected_keys = self.select_keys(cmd_list)

        all_items = self.db.get_items()
        dois = {i['DOI'].lower(): i['key'] for i in all_items if 'DOI' in i}
        items = [i for i in all_items if i['key'] in selected_keys]

        for item in items:
            key = item['key']
            if 'DOI' in item:
                doi = item['DOI']
                doi_relations_dict = self.get_relations_by_doi(doi)
                relations = doi_relations_dict['citing'] + doi_relations_dict['cited_by']
                relations = ['http://zotero.org/users/' + self.db.user_id + '/items/'
                             + dois[doi] for doi in relations if doi in dois]
                if relations == []:
                    items.remove(item)
                    print('Skipped', key, '. No relations found.')
                    continue
                else:
                    print('Relations found:', relations)

                if 'relations' in item:
                    current_relations = item['relations'].get('dc:relation', [])
                    if set(relations) <= set(current_relations):
                        items.remove(item)
                        print('Skipped', key, '. No update necessary.')
                        continue
                    relations_dict = {'dc:relation': list(set(relations + current_relations))}
                    item['relations'].update(relations_dict)
                else:
                    relations_dict = {'dc:relation': relations}
                    item['relations'] = relations_dict
            else:
                print('Skipped', key, '. No DOI found.')
                items.remove(item)

        if len(items) > 0:
            if self.db.update_items(items):
                print('Update successful')

    def execute_add_pdf(self, cmd_list):
        if len(cmd_list) == 0:
            selected_keys = self.selected_keys
            print('Add for previously selected papers.')
        else:
            selected_keys = select_keys(cmd_list)

        attachments = self.db.get_attachments(selected_keys)[0]
        if len(attachments) > 0:
            print('Attachments already present')
            print(attachments)

        # input = self.session.prompt('>>Are you sure? y/n: ')
        # if input == 'y':
        #     scihub = SciHub(use_fallback=True)
        #     item_data = self.db.get_items(selected_keys)[0]
        #
        #     file_name = self.build_file_name(item_data)
        #
        #     if 'DOI' in item_data:
        #         result = scihub.download(item_data['DOI'], path=self.paper_dir+file_name)
        #     elif 'url' in item_data:
        #         result = scihub.download(item_data['url'], path=self.paper_dir+file_name)
        #     else:
        #         print('No DOI/URL found, please provide:')
        #         url = self.session.prompt('>>')
        #         result = scihub.download(url, path=self.paper_dir+file_name)
        #
        #     if 'err' in result:
        #         warnings.warn("Could not retrieve file. Attachment creation skipped.")
        #     else:
        #         created_key = self.db.create_attachment(file_name, selected_keys)
        #         print('Created key', created_key)
        #         return created_key

    def select_keys(self, cmd_list):
        selected = ' '.join(cmd_list)
        if selected == 'none':
            selected_keys = None
        elif selected == 'all':
            selected_keys = self.papers.keys()
        else:
            selected_keys = self.papers_reverse[selected]
        print('Selected:', selected_keys)
        return selected_keys

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

    def get_relations_by_doi(self, doi):
        oc = OpenCitations()
        req = Requester(wait_time=0.1, logging=None)
        relations_dict = {}
        for util in ['references', 'citations']:
            oc.build_url(util=util)
            url = oc.get_url(util=util, segments=[doi], settings={'format': 'json'})
            result = req.request_url(url).json()

            if util == 'references':
                relations_dict['citing'] = [r['cited'] for r in result]
            else:
                relations_dict['cited_by'] = [r['citing'] for r in result]
        req.close()

        return relations_dict
