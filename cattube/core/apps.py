from django.apps import AppConfig
from django.core.checks import register, Critical
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


class CoreConfig(AppConfig):
    name = 'cattube.core'

    def ready(self):
        register(check_tl_index_exists)
