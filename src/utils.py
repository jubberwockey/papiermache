import re


def get_doi(item):
    """
    retrieve DOI from DOI data field for zotero item data, otherwise parse
    DOI from URL or items extra data field.

    Returns:
        doi or None
    """
    def get_match(s, regex):
        r = re.compile(regex, re.IGNORECASE)
        match = r.search(s)
        if match:
            return match.group()

    r = r'10.\d{4,9}\/[-._;()/:A-Z0-9]+'
    # URLs do funny stuff, e.g. http://oxfordhandbooks.com/view/10.1093/oxfordhb/9780195399820.001.0001/oxfordhb-9780195399820
    return item.get('DOI') or get_match(item.get('extra', ''), r) # or get_match(item.get('url', ''), r)
