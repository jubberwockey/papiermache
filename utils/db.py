import os
import warnings
from sqlite3 import connect
from pyzotero.zotero import Zotero
import json



class ZoteroDatabase():

    def __init__(self, local=True):
        self.user_id = os.environ['ZOTERO_USER_ID']
        self.paper_dir = os.environ['PAPER_PATH']
        self.zot = Zotero(self.user_id, 'user',
                          os.environ['ZOTERO_API_KEY'], preserve_json_order=True)
        if local == True:
            self.cursor = self.connect()
        else:
            self.cursor = None

    def connect(self):
        """
        Connect to local zotero database.

        Returns:
            cursor instance
        """
        conn = connect(os.environ['ZOTERO_DB_PATH'])
        return conn.cursor()

    def close_connection(self):
        """
        Properly close connection to local database.
        """
        if self.cursor is not None:
            return self.cursor.close()

    def build_sql(self, sql, keys=[], parent_keys=[], item_type='', tags=[], limit=-1, groupby=[]):
        """
        Build complete SQL statement from sql stub to query the zotero database.

        Arguments:
            sql: sql stub to use
            keys: list of keys to filter for
            parent_keys: list of parent keys to filter for, if applicable
            item_type: filter for e.g. 'journalArticle' etc. for syntax see:
            https://www.zotero.org/support/dev/web_api/v3/basics#search_syntax
            tags: filter for tags, currently not implemented.
            limit: number of items to retrieve. If -1, return all items
            groupby: list of keys to group by
        """
        if len(keys) > 0:
            keys_str = ','.join(map(lambda s: "'{}'".format(s), keys))
            sql += "\nAND i.key IN ({})".format(keys_str)

        if len(parent_keys) > 0:
            parent_keys_str = ','.join(map(lambda s: "'{}'".format(s), parent_keys))
            sql += "\nAND pi.key IN ({})".format(parent_keys_str)

        if len(item_type) > 0:
            if item_type[0] == '-':
                negate = 'NOT '
                item_type = item_type[1:]
            else:
                negate = ''
            types = map(lambda s: "'{}'".format(s), item_type.split(' || '))
            sql += '\nAND it.typeName ' + negate + 'IN (' + ','.join(types) + ')'

        if tags != []:
            pass
            # warnings.warn("tag filter not implemented")
            # '\nAND GROUP_CONCAT(t.name) NOT LIKE "%{}%"''.format()

        if len(groupby) > 0:
            sql += "\nGROUP BY {}".format(','.join(groupby))

        # sql += "\nORDER BY i.key"

        if limit > 0:
            sql += "\nLIMIT " + str(limit)

        sql += ";"
        return sql

    def get_items(self, keys=[], item_type='', tags=[], limit=-1, local_cursor=None, use_cache=False):
        """
        Gets list of zotero data items from either the local database or through
        the zotero API.

        Arguments:
            keys: filter for keys, see build_sql
            item_type: filter for item types, see build_sql
            tags: filter for tags, see build_sql
            limit: limit returned items, see build_sql
            local_cursor: if None, get items over API. There is a limit to
            retrieved items. If local cursor specified, use the local database
            use_cache: if True, use syched cache to from the zotero API to
            return items from local database. Possibly faster, but filtering not
            implemented.

        Returns:
            list of zotero data items conforming to the zotero API format
        """
        if not isinstance(keys, list):
            keys = [keys]

        if not isinstance(tags, list):
            tags = [tags]

        cursor = local_cursor or self.cursor

        if cursor is None:
            keys_str = ','.join(keys)
            items = self.zot.items(itemKey=keys_str, itemType=item_type, tag=tags, limit=limit)
            items = [i['data'] for i in items]
        else:
            if use_cache == False:
                items = self.get_items_data_local(local_cursor, keys, item_type, tags, limit)
                creators_data = self.get_items_creators_local(local_cursor, keys, item_type, tags, limit)
                tags_data = self.get_items_tags_local(local_cursor, keys, item_type, tags, limit)
                relations_data = self.get_items_relations_local(local_cursor, keys, item_type, tags, limit)
                collections_data = self.get_items_collections_local(local_cursor, keys, item_type, tags, limit)
                for i in items:
                    if i['key'] in creators_data:
                        i['creators'] = creators_data[i['key']]
                    if i['key'] in tags_data:
                        i['tags'] = tags_data[i['key']]
                    if i['key'] in relations_data:
                        i['relations'] = relations_data[i['key']]
                    if i['key'] in collections_data:
                        i['collections'] = collections_data[i['key']]
            else:
                warnings.warn("Filters not fully implemented")
                sql = """SELECT s.data FROM syncCache s;"""
                cursor.execute(sql)
                columns = [c[0] for c in cursor.description]
                data = cursor.fetchall()
                items = [json.loads(i[0])['data'] for i in data]
                if len(keys) > 0:
                    items = [i for i in items if i['key'] in keys]
                if len(item_type) > 0:
                    pass
                if limit >= 0:
                    items = items[0:limit]

            if len(tags) > 0:
                items = [i for i in items if all(t in [t.get('tag') for t in i.get('tags', {})] for t in tags)]

        return items

    def get_notes(self, keys=[], parent_keys=[], tags=[], limit=-1, local_cursor=None):
        """
        Retrieves note items from local database of zotero API.

        Arguments:
            keys: filter for keys of the note item(!), see build_sql
            parent_keys: filter for keys of parent items (i.e. publications)
            item_type: filter for item types, see build_sql
            tags: filter for tags, see build_sql
            limit: limit returned items, see build_sql
            local_cursor: if None, get items over API. There is a limit to
            retrieved items. If local cursor specified, use the local database
        """
        if not isinstance(keys, list):
            keys = [keys]

        if not isinstance(parent_keys, list):
            parent_keys = [parent_keys]

        cursor = local_cursor or self.cursor

        item_type = 'note'

        if cursor is None:
            if parent_keys == []:
                keys_str = ','.join(keys)
                items = self.zot.items(itemKey=keys_str, itemType=item_type, tag=tags, limit=limit)
                items = [i['data'] for i in items]
            else:
                warnings.warn("parent_keys not supported for remote database.")
        else:
            items = self.get_notes_data_local(local_cursor, keys, parent_keys, tags, limit)
            tags_data = self.get_items_tags_local(local_cursor, keys, item_type, tags, limit)
            relations_data = self.get_items_relations_local(local_cursor, keys, item_type, tags, limit)
            collections_data = self.get_items_collections_local(local_cursor, keys, item_type, tags, limit)
            for i in items:
                if i['key'] in tags_data:
                    i['tags'] = tags_data[i['key']]
                if i['key'] in relations_data:
                    i['relations'] = relations_data[i['key']]
                if i['key'] in collections_data:
                    i['collections'] = collections_data[i['key']]

        return items

    def get_attachments(self, keys=[], parent_keys=[], tags=[], limit=-1, local_cursor=None):
        """
        Retrieves attachment items from local database of zotero API.

        Arguments:
            keys: filter for keys of the note item(!), see build_sql
            parent_keys: filter for keys of parent items (i.e. publications)
            item_type: filter for item types, see build_sql
            tags: filter for tags, see build_sql
            limit: limit returned items, see build_sql
            local_cursor: if None, get items over API. There is a limit to
            retrieved items. If local cursor specified, use the local database
        """
        if not isinstance(keys, list):
            keys = [keys]

        if not isinstance(parent_keys, list):
            parent_keys = [parent_keys]

        cursor = local_cursor or self.cursor

        item_type = 'attachment'

        if cursor is None:
            if parent_keys == []:
                keys_str = ','.join(keys)
                items = self.zot.items(itemKey=keys_str, itemType=item_type, tag=tags, limit=limit)
                items = [i['data'] for i in items]
            else:
                warnings.warn("parent_keys not supported for remote database.")
        else:
            items = self.get_attachments_data_local(local_cursor, keys, parent_keys, tags, limit)
            tags_data = self.get_items_tags_local(local_cursor, keys, item_type, tags, limit)
            relations_data = self.get_items_relations_local(local_cursor, keys, item_type, tags, limit)
            for i in items:
                if i['key'] in tags_data:
                    i['tags'] = tags_data[i['key']]
                if i['key'] in relations_data:
                    i['relations'] = relations_data[i['key']]

        return items


    def get_items_data_local(self, cursor=None, keys=[], item_type='', tags=[], limit=-1):
        """
        Retrieves item data from local database to build zotero item.

        Arguments:
            cursor: Cursor instance to local database
            keys: filter for keys of the note item(!), see build_sql
            parent_keys: filter for keys of parent items (i.e. publications)
            item_type: filter for item types, see build_sql
            tags: filter for tags, see build_sql
            limit: limit returned items, see build_sql
        """
        if not isinstance(keys, list):
            keys = [keys]

        cursor = cursor or self.cursor

        if cursor is None:
            warnings.warn("sqlite cursor required")
        else:
            sql = """SELECT
                i.key,
                i.version,
                MAX(it.typeName) AS itemType,
                MAX(CASE WHEN fieldName = 'title' THEN value END) AS title,
                MAX(CASE WHEN fieldName = 'url' THEN value END) AS url,
                MAX(CASE WHEN fieldName = 'volume' THEN value END) AS volume,
                MAX(CASE WHEN fieldName = 'issue' THEN value END) AS issue,
                MAX(CASE WHEN fieldName = 'pages' THEN value END) AS pages,
                MAX(CASE WHEN fieldName = 'publicationTitle' THEN value END) AS publicationTitle,
                MAX(CASE WHEN fieldName = 'ISSN' THEN value END) AS ISSN,
                MAX(CASE WHEN fieldName = 'date' THEN value END) AS date,
                MAX(CASE WHEN fieldName = 'DOI' THEN value END) AS DOI,
                MAX(CASE WHEN fieldName = 'accessDate' THEN value END) AS accessDate,
                MAX(CASE WHEN fieldName = 'libraryCatalog' THEN value END) AS libraryCatalog,
                MAX(CASE WHEN fieldName = 'language' THEN value END) AS language,
                MAX(CASE WHEN fieldName = 'abstractNote' THEN value END) AS abstractNote,
                MAX(CASE WHEN fieldName = 'shortTitle' THEN value END) AS shortTitle,
                MAX(CASE WHEN fieldName = 'place' THEN value END) AS place,
                MAX(CASE WHEN fieldName = 'publisher' THEN value END) AS publisher,
                MAX(CASE WHEN fieldName = 'ISBN' THEN value END) AS ISBN,
                MAX(CASE WHEN fieldName = 'callNumber' THEN value END) AS callNumber,
                MAX(CASE WHEN fieldName = 'numPages' THEN value END) AS numPages,
                MAX(CASE WHEN fieldName = 'extra' THEN value END) AS extra,
                MAX(CASE WHEN fieldName = 'bookTitle' THEN value END) AS bookTitle,
                MAX(CASE WHEN fieldName = 'journalAbbreviation' THEN value END) AS journalAbbreviation,
                MAX(CASE WHEN fieldName = 'edition' THEN value END) AS edition,
                MAX(CASE WHEN fieldName = 'series' THEN value END) AS series,
                MAX(CASE WHEN fieldName = 'seriesNumber' THEN value END) AS seriesNumber,
                MAX(CASE WHEN fieldName = 'institution' THEN value END) AS institution,
                MAX(CASE WHEN fieldName = 'reportNumber' THEN value END) AS reportNumber,
                MAX(CASE WHEN fieldName = 'conferenceName' THEN value END) AS conferenceName,
                MAX(CASE WHEN fieldName = 'proceedingsTitle' THEN value END) AS proceedingsTitle,
                MAX(CASE WHEN fieldName = 'reportType' THEN value END) AS reportType,
                MAX(CASE WHEN fieldName = 'seriesTitle' THEN value END) AS seriesTitle,
                MAX(CASE WHEN fieldName = 'thesisType' THEN value END) AS thesisType,
                MAX(CASE WHEN fieldName = 'university' THEN value END) AS university,
                MAX(CASE WHEN fieldName = 'archive' THEN value END) AS archive,
                MAX(CASE WHEN fieldName = 'rights' THEN value END) AS rights,
                MAX(CASE WHEN fieldName = 'websiteTitle' THEN value END) AS websiteTitle,
                MAX(CASE WHEN fieldName = 'encyclopediaTitle' THEN value END) AS encyclopediaTitle,
                MAX(CASE WHEN fieldName = 'websiteType' THEN value END) AS websiteType,
                MAX(CASE WHEN fieldName = 'archiveLocation' THEN value END) AS archiveLocation,
                MAX(CASE WHEN fieldName = 'blogTitle' THEN value END) AS blogTitle,
                MAX(CASE WHEN fieldName = 'manuscriptType' THEN value END) AS manuscriptType,
                MAX(dateAdded) AS dateAdded,
                MAX(dateModified) AS dateModified
            FROM items i
            LEFT JOIN itemData id ON i.itemID = id.itemID
            LEFT JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            LEFT JOIN itemTags itg ON i.itemID = itg.itemID
            LEFT JOIN tags t ON itg.tagID = t.tagID

            LEFT JOIN fields f ON id.fieldID = f.fieldID
            LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID
            WHERE TRUE"""

            sql = self.build_sql(sql, keys, [], item_type, tags, limit, groupby=['i.key'])

            cursor.execute(sql)
            columns = [c[0] for c in cursor.description]
            data = cursor.fetchall()

            full_item_dict = [dict(zip(columns, item)) for item in data]

            items_list = list(map(lambda i: {k:v for k, v in i.items() if v is not None}, full_item_dict))
            return items_list

    def get_notes_data_local(self, cursor=None, keys=[], parent_keys=[], tags=[], limit=-1):
        """
        Retrieves notes data from local database to build zotero item.

        Arguments:
            cursor: Cursor instance to local database
            keys: filter for keys of the note item(!), see build_sql
            parent_keys: filter for keys of parent items (i.e. publications)
            tags: filter for tags, see build_sql
            limit: limit returned items, see build_sql
        """
        if not isinstance(keys, list):
            keys = [keys]

        cursor = cursor or self.cursor

        if cursor is None:
            warnings.warn("sqlite cursor required")
        else:
            sql = """SELECT
            	i.key,
                i.version,
            	pi.key AS parentItem,
                it.typeName AS itemType,
            	"in".note
            FROM items i
            LEFT JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            LEFT JOIN itemNotes "in" ON i.itemID = "in".itemID
            LEFT JOIN items pi ON "in".parentItemID = pi.itemID
            WHERE TRUE
            """
            sql = self.build_sql(sql, keys, parent_keys, 'note', tags, limit)

            cursor.execute(sql)
            columns = [c[0] for c in cursor.description]
            data = cursor.fetchall()

            notes_dict = [dict(zip(columns, item)) for item in data]

            notes_list = list(map(lambda i: {k:v for k, v in i.items() if v is not None}, notes_dict))
            return notes_list

    def get_attachments_data_local(self, cursor=None, keys=[], parent_keys=[], tags=[], limit=-1):
        """
        Retrieves attachment data from local database to build zotero item.

        Arguments:
            cursor: Cursor instance to local database
            keys: filter for keys of the note item(!), see build_sql
            parent_keys: filter for keys of parent items (i.e. publications)
            tags: filter for tags, see build_sql
            limit: limit returned items, see build_sql
        """
        if not isinstance(keys, list):
            keys = [keys]

        cursor = cursor or self.cursor

        if cursor is None:
            warnings.warn("sqlite cursor required")
        else:
            sql = """SELECT
            	i.key,
                i.version,
            	pi.key AS parentItem,
            	it.typeName AS itemType,
            	CASE ia.linkMode
            		WHEN 0 THEN 'imported_file'
            		WHEN 1 THEN 'imported_url'
            		WHEN 2 THEN 'linked_file'
            		WHEN 3 THEN 'linked_url'
            	END AS linkMode,
            	ia.contentType,
            	ia.path,
            	c.charset,
            	"in".note,
            	MAX(CASE WHEN f.fieldName = 'title' THEN value END) AS 'title',
            	MAX(CASE WHEN f.fieldName = 'url' THEN value END) AS 'url',
            	MAX(CASE WHEN f.fieldName = 'accessDate' THEN value END) AS 'accessDate',
            	i.dateAdded,
            	i.dateModified
            FROM items i
            LEFT JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            LEFT JOIN itemAttachments ia ON i.itemID = ia.itemID
            LEFT JOIN items pi ON ia.parentItemID = pi.itemID
            LEFT JOIN charsets c ON ia.charsetID = c.charsetID
            LEFT JOIN itemData id ON i.itemID = id.itemID
            LEFT JOIN fields f ON id.fieldID = f.fieldID
            LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID
            LEFT JOIN itemNotes "in" ON i.itemID = "in".ItemID
            WHERE TRUE
            """
            sql = self.build_sql(sql, keys, parent_keys, 'attachment', tags, limit, groupby=['i.key'])

            cursor.execute(sql)
            columns = [c[0] for c in cursor.description]
            data = cursor.fetchall()

            attachments_dict = [dict(zip(columns, item)) for item in data]

            attachments_list = list(map(lambda i: {k:v for k, v in i.items() if v is not None}, attachments_dict))
            return attachments_list

    def get_items_creators_local(self, cursor=None, keys=[], item_type='', tags=[], limit=-1):
        """
        Retrieves creator data from local database to build zotero item.

        Arguments:
            cursor: Cursor instance to local database
            keys: filter for keys of the note item(!), see build_sql
            item_type: filter for item types, see build_sql
            tags: filter for tags, see build_sql
            limit: limit returned items, see build_sql
        """
        if not isinstance(keys, list):
            keys = [keys]

        cursor = cursor or self.cursor

        if cursor is None:
            warnings.warn("sqlite cursor required")
        else:
            sql = """SELECT
                i.key,
                ct.creatorType,
                c.firstName,
                c.lastName
            FROM items i
            LEFT JOIN itemCreators ic ON i.itemID = ic.itemID
            LEFT JOIN creators c ON ic.creatorID = c.creatorID
            LEFT JOIN creatorTypes ct ON ic.creatorTypeID = ct.creatorTypeID
            LEFT JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            LEFT JOIN itemTags itg ON i.itemID = itg.itemID
            LEFT JOIN tags t ON itg.tagID = t.tagID
            WHERE ct.creatorType IS NOT NULL
            """

            sql = self.build_sql(sql, keys, [], item_type, tags, limit, groupby=['i.key', 'c.firstName', 'c.lastName'])

            cursor.execute(sql)
            columns = [c[0] for c in cursor.description]
            data = cursor.fetchall()

            creators_dict = {creator[0]: [] for creator in data}
            for creator in data:
                creators_dict[creator[0]].append(dict(zip(columns[1:], creator[1:])))

            return creators_dict

    def get_items_tags_local(self, cursor=None, keys=[], item_type='', tags=[], limit=-1):
        """
        Retrieves tags data from local database to build zotero item.

        Arguments:
            cursor: Cursor instance to local database
            keys: filter for keys of the note item(!), see build_sql
            item_type: filter for item types, see build_sql
            tags: filter for tags, see build_sql
            limit: limit returned items, see build_sql
        """
        if not isinstance(keys, list):
            keys = [keys]

        cursor = cursor or self.cursor

        if cursor is None:
            warnings.warn("sqlite cursor required")
        else:
            sql = """SELECT
                i.key,
                t.name AS tag,
                it.type
            FROM items i
            LEFT JOIN itemTags it ON i.itemID = it.itemID
            LEFT JOIN tags t ON it.tagID = t.tagID
            LEFT JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE it.type IS NOT NULL
            """

            sql = self.build_sql(sql, keys, [], item_type, tags, limit, groupby=['i.key', 't.name'])

            cursor.execute(sql)
            columns = [c[0] for c in cursor.description]
            data = cursor.fetchall()

            tags_dict = {tag[0]: [] for tag in data}
            for tag in data:
                # tags_dict[tag[0]].append({'tag': tag[1]} if tag[2] == 0 else dict(zip(columns[1:], tag[1:])))
                # last line omits manual tags type. TODO: maybe following line
                # can enforce manual tags if they coincide with automatic ones:
                tags_dict[tag[0]].append(dict(zip(columns[1:], tag[1:])))

            return tags_dict

    def get_items_relations_local(self, cursor=None, keys=[], item_type='', tags=[], limit=-1):
        """
        Retrieves relations data from local database to build zotero item.

        Arguments:
            cursor: Cursor instance to local database
            keys: filter for keys of the note item(!), see build_sql
            item_type: filter for item types, see build_sql
            tags: filter for tags, see build_sql
            limit: limit returned items, see build_sql
        """
        if not isinstance(keys, list):
            keys = [keys]

        cursor = cursor or self.cursor

        if cursor is None:
            warnings.warn("sqlite cursor required")
        else:
            sql = """SELECT
                i.key,
                rp.predicate,
                ir.object
            FROM items i
            LEFT JOIN itemRelations ir ON i.itemID = ir.itemID
            LEFT JOIN relationPredicates rp ON ir.predicateID = rp.predicateID
            LEFT JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE ir.object IS NOT NULL
            """

            sql = self.build_sql(sql, keys, [], item_type, tags, limit, groupby=['i.key', 'ir.object'])

            cursor.execute(sql)
            columns = [c[0] for c in cursor.description]
            data = cursor.fetchall()

            relations_dict = {rel[0]: {} for rel in data}
            for rel in data:
                relations_dict[rel[0]].setdefault(rel[1], []).append(rel[2])


            return relations_dict

    def get_items_collections_local(self, cursor=None, keys=[], item_type='', tags=[], limit=-1):
        """
        Retrieves collections data from local database to build zotero item.

        Arguments:
            cursor: Cursor instance to local database
            keys: filter for keys of the note item(!), see build_sql
            item_type: filter for item types, see build_sql
            tags: filter for tags, see build_sql
            limit: limit returned items, see build_sql
        """
        if not isinstance(keys, list):
            keys = [keys]

        cursor = cursor or self.cursor

        if cursor is None:
            warnings.warn("sqlite cursor required")
        else:
            sql = """SELECT
                i.key,
                c.key AS collection_key,
                c.collectionName
            FROM items i
            LEFT JOIN collectionItems ci ON i.itemID = ci.itemID
            LEFT JOIN collections c ON ci.collectionID = c.collectionID
            LEFT JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
            WHERE c.key IS NOT NULL
            """

            sql = self.build_sql(sql, keys, [], item_type, tags, limit, groupby=['i.key', 'c.key'])

            cursor.execute(sql)
            columns = [c[0] for c in cursor.description]
            data = cursor.fetchall()

            collections_dict = {coll[0]: [] for coll in data}
            for coll in data:
                collections_dict[coll[0]].append(coll[1])

            return collections_dict

    def get_autocompletes(self, local_cursor=None):
        """
        Provides a convenience dictionary for building the autocomplete engine.
        Data is retrieved from the local database only, not the zotero API!
        Returns only entries with a title or short title!
        For some reason first author in the database does not necessarily match
        first author in the zotero UI!

        Arguments:
            local_cursor: cursor for local database. If None, attempt using the
            cursor defined elsewhere in the instance.

        Returns:
            dict with database key and corresponding name for the autocomplete
            engine: First author name, year - title.
        """

        sql = """SELECT
            i.key,
            --c.firstName,
            c.lastName,
            MAX(CASE WHEN fieldName = 'shortTitle' THEN value END) AS shortTitle,
            MAX(CASE WHEN fieldName = 'title' THEN value END) AS title,
            MAX(CASE WHEN fieldName = 'date' THEN SUBSTR(value, 0, INSTR(value, '-')) END) AS year
        FROM items i
        LEFT JOIN itemCreators ic ON i.itemID = ic.itemID
        LEFT JOIN creators c ON ic.creatorID = c.creatorID
        LEFT JOIN creatorTypes ct ON ic.creatorTypeID = ct.creatorTypeID
        LEFT JOIN itemData id ON i.itemID = id.itemID
        LEFT JOIN fields f ON id.fieldID = f.fieldID
        LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID
        WHERE ic.orderIndex = 0 -- only first author
        AND fieldName IN ('title', 'shortTitle', 'date')
        GROUP BY i.key;"""

        cursor = local_cursor or self.cursor

        cursor.execute(sql)
        columns = [c[0] for c in cursor.description]
        data = cursor.fetchall()

        items_list = [dict(zip(columns, item)) for item in data]
        autocomplete_dict = {i['key']: (i['lastName'] or 'No Author') + ', ' + (i['year'] or 'xxxx') + ' - '
             + (i['shortTitle'] or i['title'] or 'Unknown Title') for i in items_list}
        return autocomplete_dict

    def create_attachment(self, file_name, parent_key=None, local_cursor=None):
        """
        Creates an attachment item for a corresponding parent key in the zotero
        cloud. Currently only pdf files in the default storage location
        supported.

        Arguments:
            file_name: File name incl. pdf extension
            parent_key: key of the parent item, if attachment should be attached
            to it
            local_cursor: currently not supported, items will be created in the
            zotero cloud

        Returns:
            key of the created item if successful, otherwise None
        """
        if local_cursor is not None:
            warnings.warn("Not implemented. Modifying local db is dangerous")
        else:
            attachment = self.zot.item_template('attachment', 'linked_file')
            attachment['title'] = file_name
            attachment['path'] = 'attachments:' + file_name
            attachment['contentType'] = 'application/pdf'
            self.zot.check_items([attachment])
            response = self.zot.create_items([attachment], parentid=parent_key)
            if '0' in response['success']:
                created_key = response['success']['0']
                return created_key
            else:
                warnings.warn("Attachment creation failed.")
                print(response['failed'])
                return None

    def update_items(self, items):
        """
        Update item data in the zotero cloud.

        Arguments:
            items: list of item data dictionaries. dictionaries must have form
            of zotero API. each dictionary must have a 'version' key with the
            latest version of the item in the zotero cloud, otherwise item will
            not be updated.

        Returns:
            True if successful
        """
        self.zot.check_items(items)
        return self.zot.update_items(items)
