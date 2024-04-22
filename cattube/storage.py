import hashlib
from urllib.parse import urlencode

from django.core.cache import cache
from storages.backends.s3 import S3Storage


class CachedS3Storage(S3Storage):
    """
    Cache signed URLs to avoid generating new ones every time we render a page. This allows the browser to cache
    thumbnail images etc.
    From https://stackoverflow.com/a/77668592/33905
    """
    def url(self, name, parameters=None, expire=None, http_method=None):
        if expire is None:
            expire = self.querystring_expire

        # Cache the result for 3/4 of the temp_url's lifetime.
        timeout = int(expire * 0.75)

        # Specify a Cache-Control header for B2 to set in the response so that the browser will cache the image
        # if parameters == None:
        #     parameters = {}
        # parameters['ResponseCacheControl'] = f'max-age={timeout}'

        params = "?{}".format(urlencode(parameters)) if parameters else ""

        # Add a prefix to avoid conflicts with other apps
        key = f"CachedS3Storage_{name}_{expire}_{params}_{http_method}"
        key = hashlib.md5(key.encode()).hexdigest()

        # Look up the key in the cache
        result = cache.get(key)
        if result is not None:
            return result

        # No cached value exists, follow the usual logic
        result = super().url(name, parameters=parameters, expire=expire, http_method=http_method)

        cache.set(key, result, timeout)

        return result
