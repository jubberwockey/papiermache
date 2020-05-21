import pytest
from src.utils import (get_doi)
from sqlite3 import Cursor

def test_get_doi_from_doi():
    item = {'DOI': '10.1016/j.jclepro.2016.10.039'}
    assert get_doi(item) == '10.1016/j.jclepro.2016.10.039'

def test_get_doi_from_url():
    item = {'url': 'http://link.springer.com/10.1007/s10902-017-9921-7'}
    assert get_doi(item) == '10.1007/s10902-017-9921-7'

def test_get_doi_from_extra():
    item = {'extra': '_eprint: https://onlinelibrary.wiley.com/doi/pdf/10.1111/irel.12227\nDOI: 10.3386/w20973'}
    assert get_doi(item) == '10.1111/irel.12227'
