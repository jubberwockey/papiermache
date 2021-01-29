import pytest
from src.dispatcher import Dispatcher

@pytest.fixture
def d():
    return Dispatcher(session=None)

def test_build_completer(d):
    pass

def test_get_completer(d):
    assert d.completer == d.get_completer()

def test_get_exit_commands(d):
    assert d.exit_cmds == d.get_exit_commands()

def test_shutdown(d):
    pass

def test_execute(d):
    pass

def test_dispatch(d):
    pass

def test_execute_find(d):
    pass

def test_execute_select(d):
    pass

def test_execute_add_relations(d):
    pass

def test_execute_add_pdf(d):
    pass

def test_execute_backup(d):
    pass

def test_download_file(d):
    pass

def test_select_keys(d):
    pass

def test_get_relations_by_doi(d):
    pass

def test_item_add_relations(d):
    pass
