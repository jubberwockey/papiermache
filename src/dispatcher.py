"""
Dispatches incoming commands
"""

import os
import sys
import warnings
import shutil
import datetime
import requests
from prompt_toolkit.completion import NestedCompleter, WordCompleter, merge_completers
from lisc.requester import Requester
from lisc.urls.open_citations import OpenCitations
from src.db import ZoteroDatabase
from src.scihub import SciHub
import src.utils as utils
import unicodedata
import concurrent.futures as cf
import copy
import json

class Dispatcher():

    def __init__(self, session, local=True):
        self.exit_cmds = ['exit', 'q', 'quit']
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

        paper_completions = WordCompleter(self.papers.values())
        tag_completions = WordCompleter(self.tags.keys())

        selections = {
            'all': None,
            'none': None,
            'collection': None,
            'tags': tag_completions,
            }

        paper_selection_completions = merge_completers([NestedCompleter.from_nested_dict(selections),
                                                        paper_completions])

        self.completions = {
            'find': None,
            'select': paper_selection_completions,
            'backup': None,
            'add': {
                'pdf': paper_selection_completions,
                'relations': paper_selection_completions,
                'link': paper_completions,
                },
            'fix': {
                'path': paper_selection_completions,
                'names': paper_selection_completions,
                }
            }
        self.completions.update({c: None for c in self.get_exit_commands()})

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

    # def verify_command(self, cmd_list):
    #     """
    #     Checks if command follows structure of a valid command.
    #     still very fishy, validates every word...
    #     """
    #     def recursive_verify(cmd_list, commands):
    #         if len(cmd_list) > 0:
    #             cmd = cmd_list.pop(0)
    #             if commands is not None:
    #                 if cmd in commands:
    #                     return recursive_verify(cmd_list, commands[cmd])
    #                 else:
    #                     warnings.warn('input not valid: {}'.format(cmd))
    #                     return False
    #             # collides with free-form input:
    #             else:
    #                 warnings.warn('too many inputs: {}'.format(cmd))
    #                 return False
    #         else:
    #             if commands is not None:
    #                 warnings.warn('additional input missing')
    #                 return False
    #             else:
    #                 return True
    #     # recursive_verify manipulates list, therefore copy:
    #     cmd_list_copy = list(cmd_list)
    #     return recursive_verify(cmd_list_copy, self.completions)

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
            self.execute_select(cmd_list)
        elif execute_cmd == 'add':
            execute_cmd = cmd_list.pop(0)
            if execute_cmd == 'pdf':
                self.execute_add_pdf(cmd_list)
            if execute_cmd == 'relations':
                self.execute_add_relations(cmd_list)
            if execute_cmd == 'link':
                self.execute_add_link(cmd_list)
        elif execute_cmd == 'fix':
            execute_cmd = cmd_list.pop(0)
            if execute_cmd == 'names':
                self.execute_fix_names(cmd_list)
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
        self.selected_keys = self.select_keys(cmd_list)

    def execute_add_relations(self, cmd_list):
        """
        Search the DOI API to retrieve citation relations between publications.
        Update relations between existing publications in the database.
        If no arguments given, use publications selected by execute_select.
        """

        def submit_items(items_update):
            print('Submitting', [i['key'] for i in items_update])
            if self.db.update_items(items_update):
                print('Update successful')

        if len(cmd_list) == 0:
            selected_keys = self.selected_keys
        else:
            selected_keys = self.select_keys(cmd_list)

        if selected_keys is None:
            print("No keys selected.")
            return None

        all_items = self.db.get_items()
        dois = {i['key']: utils.get_doi(i) for i in all_items if utils.get_doi(i)}
        dois_reversed = {v: k for k, v in dois.items()}

        items = [i for i in all_items if i['key'] in selected_keys
                                      and i['key'] in dois]

        items_update = list()
        with cf.ThreadPoolExecutor() as pool:
            futures = [pool.submit(self.get_item_relations,
                                   copy.deepcopy(i), dois_reversed) for i in items]
            for f in cf.as_completed(futures):
                fres = f.result()
                if fres is not None:
                    items_update.append(fres)
                if len(items_update) >= 50: # zotero api can only handle 50 item updates
                    submit_items(items_update)
                    items_update = list()
            if len(items_update) > 0:
                submit_items(items_update)

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

    def execute_add_link(self, cmd_list):
        """
        Adds a hyperlink (Zotero URL) to pdf of another item.
        Adds relation between items as well if not yet present.
        Useful for linking to chapters of books.
        ATTENTION: overwrites URL

        Accepts arguments:
            paper page: if previously 1 paper selected, link to page in paper
            paper paper page: link 1st paper to page in 2nd paper
        """
        if len(cmd_list) < 2:
            print("Too few arguments given, abort.")
            return

        page = cmd_list.pop(-1)
        try:
            page = int(page)
        except ValueError:
            print("No valid page number provided. Abort.")
            return

        ref_key = self.select_keys(cmd_list, verbose=False)[0]
        if ref_key is not None:
            # if only one key given, other key must have been provided by select command
            if self.selected_keys is None or len(self.selected_keys) != 1:
                print("None or multiple keys selected before, abort.")
                return
            else:
                selected_key = self.selected_keys[0]
        else:
            # if two papers listed, won't be found by select_keys, need to manually find first paper
            keys_str = ' '.join(cmd_list)
            for p in self.papers_reverse:
                if keys_str.startswith(p):
                    selected_key = self.papers_reverse[p]
                    ref_key = self.select_keys(keys_str[len(p)+1:].split(' '),
                                               verbose=False)[0]
            if ref_key is None:
                print("Cannot find key, abort.")
                return

        # use zotero API to retrieve children; TODO: use local db
        children = self.db.zot.children(ref_key)
        pdf_key = None
        for c in children:
            if c['data'].get('contentType', None) == 'application/pdf':
                if pdf_key is None:
                    pdf_key = c['key']
                else:
                    print("Multiple pdfs found. Abort.")
                    return
        if pdf_key is None:
            print("No pdf found")
            return

        item = self.db.get_items(keys=selected_key)[0]

        item_update = {k: v for k, v in item.items() if k in ['key', 'version']}
        item_update['url'] = 'zotero://open-pdf/library/items/{pdf_key}?page={page}'.format(pdf_key=pdf_key, page=page)
        relations_update = self.merge_item_relations(item, ref_key, verbose=False)
        if relations_update is not None:
            item_update['relations'] = relations_update
        self.db.update_items([item_update])
        print("Link updated")

    def execute_fix_names(self, cmd_list):
        """
        Fix names. In safe_mode, create blacklist
        ATTENTION: make sure to create blacklist when all items selected

        """
        if len(cmd_list) == 0:
            selected_keys = self.selected_keys
        else:
            selected_keys = self.select_keys(cmd_list)

        if selected_keys is None:
            print("No keys selected.")
            return None

        items_update = self.fix_names(selected_keys, safe_mode=True,
                                      blacklist_path='./data/blacklist.json')

        self.db.batch_update_items(items_update)

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

    def select_keys(self, cmd_list, verbose=True):
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
            selected_keys = self.tags.get(selected)
        elif selected == 'collections':
            pass
        else:
            selected = ' '.join(cmd_list)
            selected_keys = [self.papers_reverse.get(selected)]
        if verbose:
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

        Arguments
            doi: DOI str

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
            response = req.request_url(url)
            if response.status_code == 200:
                try:
                    result = response.json()
                except requests.exceptions.JSONDecodeError:
                    result = {}

            if util == 'references':
                relations_dict['citing'] = [r['cited'] for r in result]
            else:
                relations_dict['cited_by'] = [r['citing'] for r in result]
        req.close()

        return relations_dict

    def merge_item_relations(self, item, keys, verbose=True):
        """
        Merges new relations with current relations in item['relations'].

        Arguments:
            item: dict
            keys: list or str of new relation key(s)

        Returns:
            item['relations'] dict
        """
        if isinstance(keys, str):
            keys = [keys]

        item = copy.deepcopy(item)
        key = item['key']
        relations = ['http://zotero.org/users/' + self.db.user_id + '/items/' + k for k in keys]

        if len(relations) > 0:
            current_relations = item.setdefault('relations', {}).setdefault('dc:relation', [])
            if not (set(relations) <= set(current_relations)):
                item['relations']['dc:relation'] = list(set(relations + current_relations))
                if verbose:
                    print('Relations found:\n', key, self.papers[key])
                return item['relations']
            else:
                if verbose:
                    print('No update necessary:\n', key, self.papers[key])
        else:
            if verbose:
                print('No Relations found:\n', key, self.papers[key])

    def get_item_relations(self, item, dois):
        """
        Creates item dict for updating relations suited for parallelization.

        Arguments:
            item: item['data'] dict from zotero API
            dois: {doi: key} dict for all DOIs in library

        Returns:
            dict with keys ['key', 'version', 'relations']
        """
        key = item['key']
        doi = utils.get_doi(item)
        if doi:
            doi_relations_dict = self.get_relations_by_doi(doi)
            relations = doi_relations_dict['citing'] + doi_relations_dict['cited_by']
            keys = [dois[doi] for doi in relations if doi in dois]
            # relations = ['http://zotero.org/users/' + self.db.user_id + '/items/'
            #              + dois[doi] for doi in relations if doi in dois]
            relations_update = self.merge_item_relations(item, keys, verbose=True)
            if relations_update is not None:
                item_update = {k: v for k, v in item.items() if k in ['key', 'version', 'relations']}
                item_update['relations'] = relations_update
                return item_update
            #
            # if len(relations) > 0:
            #     current_relations = item.setdefault('relations', {}).setdefault('dc:relation', [])
            #     if not (set(relations) <= set(current_relations)):
            #         item_update['relations']['dc:relation'] = list(set(relations + current_relations))
            #         print('Relations found:\n', key, self.papers[key])
            #         return item_update
            #     else:
            #         print('No update necessary:\n', key, self.papers[key])
            # else:
            #     print('No Relations found:\n', key, self.papers[key])
        else:
            print('No DOI found:\n', key, self.papers[key])


    def fix_name(self, name_dict, names, safe_mode=True, blacklist=None):
        """
        Does the following things in this order:
        Adds dots to abbreviated first names.
        Tries to complete first names if present in database.
        Tries to find additional first names.
        Tries to convert full name to first name-last name style.

        Arguments:
            name_dict: dict of one creator
            names: set of tuples of all names {(firstName, lastName, (first, names, abbreviated))}
            safe_mode: bool, skip possibly ambivalent operations
            blacklist: blacklist json of creators

        Returns:
            status: -1: no changes
                    0: changed
                    >0: skipped, bitmask
            dict of changed name, otherwise None
        """
        status = 0

        if blacklist is not None:
            if name_dict in blacklist:
                print("Skipped: {} blacklisted.".format(name_dict))
                return 1, None

        fnames = name_dict['firstName']
        fnames_lst = fnames.split()
        lname = name_dict['lastName']
        lname_lst = lname.split()

        # convert full names to first name, last name
        if len(lname_lst) > 1 and fnames == '':
            if safe_mode:
                print('Safe Mode: Skipped splitting full name {}'.format(lname))
                status += 2
            else:
                fnames_lst = lname_lst[:-1]
                lname = lname_lst[-1]
                print('Splitted full name into {} {}'.format(fnames_lst, lname))

        # add dots
        names_abbr = tuple( n + '.' if len(n) == 1 else n for n in fnames_lst )
        fnames_mod = ' '.join(names_abbr)

        # TODO: find full & additional names simultaneously
        full_fnames = list()
        add_fnames = list()
        for n in names:
            if lname == n[1]:
                # check for full first names
                if names_abbr == n[2]:
                    full_fnames.append(n[0])

                # check for additional first names
                other_fnames = n[0].split()
                num_names = len(fnames_lst)
                if fnames_lst == other_fnames[:num_names] and num_names < len(other_fnames):
                    # safe mode: only change if first(!) first name not abbreviated:
                    if safe_mode:
                        if len(other_fnames[0].replace('.', '')) > 1:
                            add_fnames.append(n[0])
                        else:
                            print('Safe Mode: Skipped only abbreviated first name {} {}'.format(n[0], n[1]))
                            status += 4
                    else:
                        add_fnames.append(n[0])

        for lst in [add_fnames, full_fnames]:
            if len(lst) == 1:
                fnames_mod = lst[0]
                print('Changed {} into {} {}'.format(fnames, fnames_mod, lname))
            elif len(lst) > 1:
                print('Skipped: Multiple first names found for {} {}'.format(lst, lname))
                status += 8

        name_dict_mod = copy.deepcopy(name_dict)
        name_dict_mod['firstName'] = fnames_mod
        name_dict_mod['lastName'] = lname

        if status > 0:
            return status, None
        else:
            if name_dict_mod != name_dict:
                return status, name_dict_mod
            else:
                return -1, None

    def fix_names(self, keys=[], safe_mode=True, blacklist_path=None):
        """
        Fix names for selected keys

        Arguments
            keys: list of keys
            safe_mode: if True, skip ambivalent renamings. If blacklist_path not None, create blacklist
            blacklist_path: path to blacklist json

        """
        def create_abbr(name):
            name_lst = name.split()
            if sum(c.isalpha() for c in name) > len(name_lst):
                return tuple( n[0] + '.'  for n in name_lst )

        if blacklist_path is not None:
            try:
                with open(blacklist_path, 'r') as f:
                    blacklist = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                blacklist = None

        all_items = self.db.get_items()
        names = { ( c.get('firstName', ''), c.get('lastName', ''),
                create_abbr(c.get('firstName', '')) ) for i in all_items for c in i.get('creators', []) }

        items = self.db.get_items(keys)

        items_mod = list()
        names_skipped = list()
        for i in items:
            creators_mod = copy.deepcopy(i.get('creators', []))
            mod = 0
            for n, c in enumerate(i.get('creators', [])):
                status, name_mod = self.fix_name(c, names, safe_mode=safe_mode, blacklist=blacklist)
                if status == 0:
                    creators_mod[n] = name_mod
                    mod +=1
                elif status > 0:
                    names_skipped.append(c)
            if mod > 0:
                item_mod = {'key': i['key'], 'version': i['version'], 'creators': creators_mod}
                items_mod.append(item_mod)

        if blacklist_path is not None and safe_mode:
            skipped = [dict(t) for t in {tuple(sorted(d.items())) for d in names_skipped}]
            with open(blacklist_path, 'w') as f:
                json.dump(skipped, f, indent=4)

        return items_mod
