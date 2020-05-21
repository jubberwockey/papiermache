"""
Dispatches incoming commands
"""

import os
import sys
import warnings
import shutil
import datetime
from prompt_toolkit.completion import NestedCompleter
from lisc.requester import Requester
from lisc.urls.open_citations import OpenCitations
from src.db import ZoteroDatabase
from src.scihub import SciHub
import src.utils as utils
import unicodedata
import concurrent.futures as cf
import copy

class Dispatcher():

    def __init__(self, session, local=True):
        self.exit_cmds = ['exit', 'q', 'quit']
        self.cmd_template = {
            'find': None,
            'select': None,
            'backup': None,
            'add': {
                'pdf': None,
                'relations': None,
                },
            'fix': {
                'path': None,
                }
            }
        self.cmd_template.update({c: None for c in self.exit_cmds})
        self.paper_dir = os.environ['PAPER_PATH']

        self.session = session
        self.db = ZoteroDatabase(local=local)
        self.scihub = None

        self.completions = None
        self.papers = self.db.get_autocompletes()
        self.papers_reverse = {v: k for k, v in self.papers.items()}
        self.tags = self.db.get_autocomplete_tags()
        self.completer = self.build_completer()
        self.selected_keys = None

    def build_completer(self):
        """
        Generates autocompletes for publications for various commands.
        """

        selections = {
            'all': None,
            'none': None,
            'collection': None,
            'tags': {},
            }
        self.completions = dict(self.cmd_template)
        self.completions['select'] = selections
        self.completions['add']['pdf'] = selections
        self.completions['add']['relations'] = selections
        self.completions['fix']['path'] = selections

        paper_completions = {v: None for v in self.papers.values()}
        self.completions['select'].update(paper_completions)
        self.completions['add']['pdf'].update(paper_completions)
        self.completions['add']['relations'].update(paper_completions)
        self.completions['fix']['path'].update(paper_completions)

        tag_completions = {v: None for v in self.tags.keys()}
        self.completions['select']['tags'].update(tag_completions)
        self.completions['add']['pdf']['tags'].update(tag_completions)
        self.completions['add']['relations']['tags'].update(tag_completions)
        self.completions['fix']['path']['tags'].update(tag_completions)

        return NestedCompleter.from_nested_dict(self.completions)

    def get_completer(self):
        """
        Returns completer instance for handling autocompletes
        """
        return self.completer

    def get_exit_commands(self):
        """
        Returns possible commands for exiting program
        """
        return self.exit_cmds

    def shutdown(self, msg=''):
        """
        Cleanup for proper shutdown of program
        """
        self.db.close_connection()
        print(msg)
        return sys.exit(0)

    def verify_command(self, cmd_list):
        """
        Checks if command follows structure of a valid command.
        still very fishy, validates every word...
        """
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
        """
        Sends input command to dispatch.
        """
        cmd = input.split()
        if len(cmd) > 0:
            self.dispatch(cmd)
        # if self.verify_command(cmd) is True:
        #     self.dispatch(cmd)

    def dispatch(self, cmd_list):
        """
        Parses input command and dispatches it to the appropriate execution
        commands.
        """
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
        elif execute_cmd == 'backup':
            self.execute_backup(cmd_list)

    def execute_find(self, cmd_list):
        """
        Find free-form input in database metadata. Return corresponding entries.
        Only key search implemented yet.
        """
        warnings.warn("Only key search implemented!")
        key = cmd_list.pop(0)
        print(self.papers.get(key))

    def execute_select(self, cmd_list):
        """
        Select one or multiple keys in the database to perform further actions
        on.
        """
        return self.select_keys(cmd_list)

    def execute_add_relations(self, cmd_list):
        """
        Search the DOI API to retrieve citation relations between publications.
        Update relations between existing publications in the database.
        If no arguments given, use publications selected by execute_select.
        """
        if len(cmd_list) == 0:
            selected_keys = self.selected_keys
        else:
            selected_keys = self.select_keys(cmd_list)

        if selected_keys is None:
            print("No keys selected.")
            return None

        all_items = self.db.get_items()
        dois = {i['DOI'].lower(): i['key'] for i in all_items if 'DOI' in i}
        items = [i for i in all_items if i['key'] in selected_keys]

        items_update = list()
        with cf.ThreadPoolExecutor() as pool:
            futures = [pool.submit(self.item_add_relations,
                                   copy.deepcopy(i), dois) for i in items]
            for f in cf.as_completed(futures):
                fres = f.result()
                if fres is not None:
                    fres = {key: fres.get(key) for key in ['key', 'version', 'relations']}
                    items_update.append(fres)
                if len(items_update) >= 50: # zotero api can only handle 50 item updates
                    print('Submitting', [i['key'] for i in items_update])
                    if self.db.update_items(items_update):
                        print('Update successful')
                    items_update = list()
            print('Submitting', [i['key'] for i in items_update])
            if self.db.update_items(items_update):
                print('Update successful')
            items_update = list()

        #     for i in items:
        #         item = copy.deepcopy(i)
        #         futures = pool.submit(self.item_add_relations, item, dois)
        # items_update = [f.result() for f in futures if f.result() is not None]
        #
        # if len(items_update) > 0:
        #     if self.db.update_items(items_update):
        #         print('Update successful')

    def execute_add_pdf(self, cmd_list):
        """
        Downloads pdfs for selected publications if no pdf present and updates
        selected publications in the database.
        If no argument given use selected publications from execute_select.
        """
        if len(cmd_list) == 0:
            selected_keys = self.selected_keys
        else:
            selected_keys = self.select_keys(cmd_list)

        if selected_keys is None:
            print("No keys selected.")
            return None

        file_types = ['pdf', 'epub', 'djvu', 'mobi', 'okular']

        items = self.db.get_items(keys=selected_keys)
        attachments = self.db.get_attachments(parent_keys=selected_keys)

        attachment_keys = [a['parentItem'] for a in attachments
                           if 'parentItem' in a and (a.get('path', '').split('.')[-1]).lower() in file_types]

        # no_attachments_dict = {i['key']: {'url': i.get('url'), 'DOI': utils.get_doi(i), 'ISBN': i.get('ISBN')}
        #                        for i in items if i['key'] not in attachment_keys}

        # no_att_items = [i for i in items if i['key'] not in attachment_keys]

        for item in items:
            key = item['key']
            if key not in attachment_keys:
                file_name = self.build_file_name(item)
                file_path = self.paper_dir + file_name

                url = utils.get_doi(item) or item['url']
                if url:
                    success = self.download_file(url, file_path)
                else:
                    success = False
                    warnings.warn("Download not successful")

                if success:
                    created_key = self.db.create_attachment(file_name, key)
                    print('Created key', created_key)
                    return created_key

    def execute_backup(self, cmd_list):
        """
        Create a backup of the local database file.
        Accepts arguments:
            no argument: use default name (zotero_timestamp.sqlite) and location
                (/home/user/Zotero/)
            file: create file.sqlite in default location
            file.ext: create file.ext in default location
            path/file: create file.sqlite in specified path
            path/file.ext: create file.ext in specified path
        """
        cmd = ' '.join(cmd_list)

        self.db.close_connection()

        db_path = os.environ['ZOTERO_DB_PATH']
        db_dir = os.path.dirname(db_path)

        if len(cmd) > 0:
            backup_dir = os.path.dirname(cmd)
            file = os.path.basename(cmd)
            _, ext = os.path.splitext(file)
            if len(ext) == 0:
                file += '.sqlite'

            if len(backup_dir) > 0:
                if os.path.isdir(backup_dir):
                    backup_path = os.path.join(backup_dir, file)
                else:
                    raise NameError("Directory does not exist.")
            else:
                backup_path = os.path.join(db_dir, file)
        else:
            file, ext = os.path.splitext(os.path.basename(db_path))
            file += '_' + datetime.datetime.now().isoformat() + ext
            backup_path = os.path.join(db_dir, file)

        if backup_path == db_path:
            raise NameError("File and backup path identical.")

        shutil.copy2(db_path, backup_path)
        self.db.cursor = self.db.connect()

        return True

    def download_file(self, url, file_path, source='scihub'):
        """
        Attempt download of pdf for given URL or DOI.

        Arguments:
            url: URL or DOI of publication
            file_path: path including file name of downloaded pdf
            source: currently only 'scihub' supported
        Returns:
            True if download successful
        """
        if source == 'scihub':
            if self.scihub is None:
                self.scihub = SciHub(use_fallback=True)
            result = self.scihub.download(url, path=file_path)
            if 'err' not in result:
                return True
            else:
                return False

    def select_keys(self, cmd_list):
        """
        Select one or multiple keys of database entries for further operations.
        """
        # selected = ' '.join(cmd_list)
        selected = cmd_list[0]
        if selected == 'none':
            selected_keys = None
        elif selected == 'all':
            selected_keys = self.papers.keys()
        elif selected == 'tags':
            selected = ' '.join(cmd_list[1:])
            selected_keys = self.tags[selected]
        elif selected == 'collections':
            pass
        else:
            selected = ' '.join(cmd_list)
            selected_keys = self.papers_reverse[selected]
        print('Selected:', selected_keys)
        return selected_keys

    def build_file_name(self, item_dict, file_type='pdf'):
        """
        Emulate file naming scheme of the zotfile extension for saved pdfs:
        name_name2_year_title.file_type
        name_et al_year_title.file_type
        Note: There is no guarantee, that the naming is identical (especially if
        year is missing or title is too long).

        Arguments:
            item_dict: item['data'] dict from zotero API
            file_type: file extension

        Returns:
            file name
        """
        if 'creators' in item_dict:
            name = item_dict['creators'][0]['lastName']
            if len(item_dict['creators']) == 2:
                name += '_' + item_dict['creators'][1]['lastName']
            elif len(item_dict['creators']) > 2:
                 name += ' et al'
        else:
            name = ''

        year = item_dict.get('date', '').split('-')[0]

        if 'shortTitle' in item_dict:
            title = item_dict['shortTitle'].split(':')[0]
        else:
            title = item_dict.get('title', '').split(':')[0]

        file_name = '_'.join([name, year, title]) + '.' + file_type
        file_name = unicodedata.normalize('NFD', file_name).encode('ascii', 'ignore').decode('utf-8')
        return file_name

    def get_relations_by_doi(self, doi):
        """
        Obtains DOIs of citing articles and cited articles for a given DOI from
        the DOI database API.

        Returns:
            dict
                'citing': DOIs which are cited in this publication
                'cited_by': DOIs of articles which cited this publication
        """
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

    def item_add_relations(self, item, dois):
        key = item['key']
        if 'DOI' in item:
            doi = item['DOI']
            doi_relations_dict = self.get_relations_by_doi(doi)
            relations = doi_relations_dict['citing'] + doi_relations_dict['cited_by']
            relations = ['http://zotero.org/users/' + self.db.user_id + '/items/'
                         + dois[doi] for doi in relations if doi in dois]

            if len(relations) > 0:
                current_relations = item.setdefault('relations', {}).setdefault('dc:relation', [])
                if not (set(relations) <= set(current_relations)):
                    item['relations']['dc:relation'] = list(set(relations + current_relations))
                    print('Relations found:\n', key, self.papers[key])
                    return item
                else:
                    print('No update necessary:\n', key, self.papers[key])
            else:
                print('No Relations found:\n', key, self.papers[key])
        else:
            print('No DOI found:\n', key, self.papers[key])
