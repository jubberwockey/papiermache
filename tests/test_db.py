import pytest
from src.db import ZoteroDatabase
from sqlite3 import Cursor

@pytest.fixture
def zot():
    return ZoteroDatabase()

def test_connect(zot):
    assert isinstance(zot.connect(), Cursor)
    zot.close_connection()

def test_build_sql(zot):
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

    assert sql_out == zot.build_sql(sql, keys=keys, parent_keys=parent_keys,
                                    item_type=item_type, limit=limit,
                                    groupby=groupby)

def test_build_sql_item_type(zot):
    sql = "SELECT"
    item_type = '-journalArticle || book'

    sql_out = """SELECT
AND it.typeName NOT IN ('journalArticle','book');"""

    assert sql_out == zot.build_sql(sql, item_type=item_type)

def test_build_sql_tags(zot):
    pass

def test_get_items_remote():
    zot = ZoteroDatabase(local=False)
    keys = ['XXLF2GYS', 'JTWSQKIS', '4SDR5E5R', 'UYJJPTXG']
    item_type = 'journalArticle'
    tags = '# important'

    items = zot.get_items(keys=keys, item_type=item_type, tags=tags)
    assert len(items) == 1
    assert items[0]['key'] == 'XXLF2GYS'

def test_get_notes_remote():
    zot = ZoteroDatabase(local=False)
    keys = ['XXLF2GYS', 'JTWSQKIS', '4SDR5E5R', 'UYJJPTXG']

    notes = zot.get_notes(keys=keys)
    assert len(notes) == 1
    assert notes[0]['key'] == '4SDR5E5R'

def test_attachments_remote():
    zot = ZoteroDatabase(local=False)
    keys = ['XXLF2GYS', 'JTWSQKIS', '4SDR5E5R', 'UYJJPTXG']

    atts = zot.get_attachments(keys=keys)
    assert len(atts) == 1
    assert atts[0]['key'] == 'JTWSQKIS'

def test_get_items_data_local(zot):
    keys = ['XXLF2GYS', 'JTWSQKIS', '4SDR5E5R', 'UYJJPTXG']
    item_type = 'journalArticle'
    tags = ['# important']

    items = zot.get_items_data_local(keys=keys, item_type=item_type,
                                     tags=tags)
    assert len(items) == 1
    assert items[0]['key'] == 'XXLF2GYS'

def test_get_notes_data_local(zot):
    keys = ['XXLF2GYS', 'JTWSQKIS', '4SDR5E5R', 'UYJJPTXG']
    parent_keys = ['FVGL3T4D']

    notes = zot.get_notes_data_local(keys=keys, parent_keys=parent_keys)
    assert len(notes) == 1
    assert notes[0]['key'] == '4SDR5E5R'

def test_get_attachments_data_local(zot):
    keys = ['XXLF2GYS', 'JTWSQKIS', '4SDR5E5R', 'UYJJPTXG']
    parent_keys = ['K5IEG43P']

    atts = zot.get_attachments_data_local(keys=keys, parent_keys=parent_keys)
    assert len(atts) == 1
    assert atts[0]['key'] == 'JTWSQKIS'

def test_get_items_creators_local(zot):
    pass

def test_get_items_tags_local(zot):
    pass

def test_get_items_relations_local(zot):
    pass

def test_get_items_collections_local(zot):
    pass

def test_get_autocompletes(zot):
    items = zot.get_items()

    ac_dict = zot.get_autocompletes()
    assert len(items) == len(ac_dict)
