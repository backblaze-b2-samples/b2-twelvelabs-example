from django.apps import AppConfig
from django.conf import settings
from django.core.checks import register, Critical, Error
from twelvelabs import APIStatusError

from cattube.settings import TWELVE_LABS_CLIENT, TWELVE_LABS_INDEX_ID


# noinspection PyUnusedLocal
def check_tl_index_exists(app_configs, **kwargs):
    """
    Get the index from Twelve Labs to validate the API key and index ID.
    """
    errors = []

    try:
        index = TWELVE_LABS_CLIENT.index.retrieve(TWELVE_LABS_INDEX_ID)
        print(f'Retrieved index "{str(index.__dict__)}"')
    except APIStatusError as e:
        errors.append(Critical('API Status Error from Twelve Labs', hint=str(e)))
    except Exception as e:
        errors.append(Critical('Exception calling Twelve Labs API', hint=str(e)))

    return errors


# noinspection PyUnusedLocal
def check_b2_storage_configuration(app_configs, **kwargs):
    """
    Reject public static URLs from the private media bucket.
    """
    errors = []
    default_options = settings.STORAGES["default"]["OPTIONS"]
    static_options = settings.STORAGES["staticfiles"]["OPTIONS"]

    if (
        static_options.get("querystring_auth") is False
        and static_options.get("bucket_name") == default_options.get("bucket_name")
    ):
        errors.append(Error(
            'B2 media and unsigned static files cannot share a bucket',
            hint='Use signed static URLs or configure a separate public static bucket.',
            id='cattube.E001',
        ))

    return errors


class CoreConfig(AppConfig):
    name = 'cattube.core'

    def ready(self):
        register(check_tl_index_exists)
        register(check_b2_storage_configuration)
