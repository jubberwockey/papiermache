import re


def get_doi(item):

    def get_match(s, regex):
        r = re.compile(regex, re.IGNORECASE)
        match = r.search(s)
        if match:
            return match.group()

    r = r'10.\d{4,9}\/[-._;()/:A-Z0-9]+'
    return item.get('DOI') or get_match(item.get('url', ''), r) or get_match(item.get('extra', ''), r)
