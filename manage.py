#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    # Apply gevent monkey-patch if we are running the huey consumer with greenlet workers.
    # See https://huey.readthedocs.io/en/latest/contrib.html#using-gevent
    if 'run_huey' in sys.argv:
        for arg in sys.argv:
            if 'greenlet' in arg:
                from gevent import monkey
                monkey.patch_all()
                break

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cattube.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(sys.argv)
