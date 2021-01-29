import pytest
from src.db import ZoteroDatabase
from sqlite3 import Cursor
from pyzotero.zotero_errors import InvalidItemFields

@pytest.fixture
def db():
    return ZoteroDatabase()

def test_connect(db):
    assert isinstance(db.connect(), Cursor)
    db.close_connection()

def test_build_sql(db):
    sql = "SELECT"
    keys = ['a', 'b']
    parent_keys = ['c', 'd']
    item_type = 'book || note'
    limit = 10
    groupby = ['e', 'f']

    sql_out = """SELECT
AND i.key IN ('a','b')
AND pi.key IN ('c','d')
AND it.typeName IN ('book','note')
GROUP BY e,f
LIMIT 10;"""

    assert sql_out == db.build_sql(sql, keys=keys, parent_keys=parent_keys,
                                    item_type=item_type, limit=limit,
                                    groupby=groupby)

def test_build_sql_item_type(db):
    sql = "SELECT"
    item_type = '-journalArticle || book'

    sql_out = """SELECT
AND it.typeName NOT IN ('journalArticle','book');"""

    assert sql_out == db.build_sql(sql, item_type=item_type)

def test_build_sql_tags(db):
    pass

def test_get_items_remote():
    db = ZoteroDatabase(local=False)
    keys = ['XXLF2GYS', 'JTWSQKIS', '4SDR5E5R', 'UYJJPTXG']
    item_type = 'journalArticle'
    tags = '# important'

    items = db.get_items(keys=keys, item_type=item_type, tags=tags)
    assert len(items) == 1
    assert items[0]['key'] == 'XXLF2GYS'

def test_get_notes_remote():
    db = ZoteroDatabase(local=False)
    keys = ['XXLF2GYS', 'JTWSQKIS', '4SDR5E5R', 'UYJJPTXG']

    notes = db.get_notes(keys=keys)
    assert len(notes) == 1
    assert notes[0]['key'] == '4SDR5E5R'

def test_attachments_remote():
    db = ZoteroDatabase(local=False)
    keys = ['XXLF2GYS', 'JTWSQKIS', '4SDR5E5R', 'UYJJPTXG']

    atts = db.get_attachments(keys=keys)
    assert len(atts) == 1
    assert atts[0]['key'] == 'JTWSQKIS'

def test_get_items_local(db):
    pass

def test_get_items_local_cache(db):
    pass

def test_get_notes_local(db):
    pass

def test_get_attachments_local(db):
    pass

def test_get_items_data_local(db):
    keys = ['XXLF2GYS', 'JTWSQKIS', '4SDR5E5R', 'UYJJPTXG']
    item_type = 'journalArticle'
    tags = ['# important']

    items = db.get_items_data_local(keys=keys, item_type=item_type,
                                     tags=tags)
    assert len(items) == 1
    assert items[0]['key'] == 'XXLF2GYS'

def test_get_notes_data_local(db):
    keys = ['XXLF2GYS', 'JTWSQKIS', '4SDR5E5R', 'UYJJPTXG']
    parent_keys = ['FVGL3T4D']

    notes = db.get_notes_data_local(keys=keys, parent_keys=parent_keys)
    assert len(notes) == 1
    assert notes[0]['key'] == '4SDR5E5R'

def test_get_attachments_data_local(db):
    keys = ['XXLF2GYS', 'JTWSQKIS', '4SDR5E5R', 'UYJJPTXG']
    parent_keys = ['K5IEG43P']

    atts = db.get_attachments_data_local(keys=keys, parent_keys=parent_keys)
    assert len(atts) == 1
    assert atts[0]['key'] == 'JTWSQKIS'

def test_get_items_creators_local(db):
    pass

def test_get_items_tags_local(db):
    pass

def test_get_items_relations_local(db):
    pass

def test_get_items_collections_local(db):
    pass

def test_get_autocompletes(db):
    items = db.get_items()

    ac_dict = db.get_autocompletes()
    assert len(items) == len(ac_dict)
    assert ac_dict['2B3ZWD3G'] == "Creutzig, 2016 - Beyond Technology"

def test_get_autocomplete_tags(db):
    pass
    db.get_items_tags_local()

def test_create_attachment(db):
    pass

def test_update_items(db):
    pass

def test_update_items_invalid_field(db):
    items = db.get_items(keys='XXLF2GYS')
    items[0]['invalid_field'] = 'invalid'

    with pytest.raises(InvalidItemFields):
        assert db.update_items(items)
