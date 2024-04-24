from urllib.parse import urlunsplit, urlsplit


# From https://codereview.stackexchange.com/a/24416/27914
def first(sequence, default=''):
    return next((x for x in sequence if x), default)


def url_path_join(*parts):
    """Normalize url parts and join them with a slash."""
    schemes, netlocs, paths, queries, fragments = zip(*(urlsplit(part) for part in parts))
    scheme = first(schemes)
    netloc = first(netlocs)
    path = '/'.join(x.strip('/') for x in paths if x)
    query = first(queries)
    fragment = first(fragments)
    return urlunsplit((scheme, netloc, path, query, fragment))
