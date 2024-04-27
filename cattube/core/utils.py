import hashlib
import hmac
import json
from datetime import timedelta, datetime
from urllib.parse import urlunsplit, urlsplit

from django.utils.safestring import mark_safe

from cattube import settings
from cattube.settings import TRANSLOADIT_SECRET


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


def load_json(obj, data_type):
    """
    Retrieve one of the video's JSON data resources, parse and return it.
    """
    file_field = getattr(obj, data_type)
    data = None
    if file_field.name:
        file_field.open(mode="rb")
        data = file_field.read()
        file_field.close()

    return json.loads(data) if data else None


def load_json_into_context(context, data_types, obj):
    """
    Populate the context with the JSON resources for the given types.
    """
    for data_type in data_types:
        context[data_type] = load_json(obj, data_type)


def verify_transloadit_signature(data):
    """
    Based on Node implementation at https://transloadit.com/docs/topics/assembly-notifications/#example
    """
    received_signature = data.get('signature')
    payload = data.get('transloadit')

    if not received_signature or not payload:
        return False

    # If the signature contains a colon, we expect it to be of format `algo:actual_signature`.
    # If there are no colons, we assume it's a legacy signature using SHA-1.
    algo_separator_index = received_signature.find(':')
    algo = 'sha1' if algo_separator_index == -1 else received_signature[0, algo_separator_index]

    calculated_signature = hmac.new(TRANSLOADIT_SECRET.encode('utf-8'),
                                    payload.encode('utf-8'),
                                    algo).hexdigest()

    return calculated_signature == received_signature[algo_separator_index + 1:]


def create_signed_transloadit_options(notify_url):
    """
    Signature calculation from
    https://transloadit.com/docs/topics/signature-authentication/#signature-python-sdk-demo
    """
    params = {
        'auth': {
            'key': settings.TRANSLOADIT_KEY,
            'expires': (timedelta(seconds=60 * 60) + datetime.utcnow()).strftime("%Y/%m/%d %H:%M:%S+00:00"),
        },
        'template_id': settings.TRANSLOADIT_TEMPLATE_ID,
    }

    if notify_url:
        params['notify_url'] = notify_url

    message = json.dumps(params, separators=(',', ':'), ensure_ascii=False)
    signature = hmac.new(settings.TRANSLOADIT_SECRET.encode('utf-8'),
                         message.encode('utf-8'),
                         hashlib.sha384).hexdigest()
    return {
        # Need to mark message as safe so Django doesn't escape the JSON, breaking the signature
        'params': mark_safe(message),
        'signature': f'sha384:{signature}'
    }
