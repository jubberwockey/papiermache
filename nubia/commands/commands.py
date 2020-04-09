from nubia import command, argument
from db import ZoteroDatabase

z = ZoteroDatabase()

@command
def version():
    """Prints version"""
    print('0.01a')
    return None

@command
@argument('keyword', description="Keyword to search for in database",
          choices=['abc', 'def'], positional=True)
def search(keyword: str):
    """Search for Keyword in Database"""
    print('search for', keyword)
