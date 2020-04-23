import re


def get_doi(item):
    """
    retrieve DOI from DOI data field for zotero item data, otherwise parse
    DOI from URL or items extra data field.
    """
    def get_match(s, regex):
        r = re.compile(regex, re.IGNORECASE)
        match = r.search(s)
        if match:
            return match.group()

    r = r'10.\d{4,9}\/[-._;()/:A-Z0-9]+'
    return item.get('DOI') or get_match(item.get('url', ''), r) or get_match(item.get('extra', ''), r)
