import importlib
import os
import sys
import unittest
from unittest.mock import Mock, patch

from django.core.exceptions import ImproperlyConfigured


BASE_ENV = {
    "TRANSLOADIT_KEY": "test-transloadit-key",
    "TRANSLOADIT_SECRET": "test-transloadit-secret",
    "TRANSLOADIT_TEMPLATE_ID": "test-template",
    "TWELVE_LABS_API_KEY": "test-twelve-key",
    "TWELVE_LABS_INDEX_ID": "test-index",
    "WEB_APPLICATION_HOST": "localhost",
}


def import_settings(env):
    sys.modules.pop("cattube.settings", None)
    with patch.dict(os.environ, {**BASE_ENV, **env}, clear=True):
        with patch("twelvelabs.TwelveLabs", return_value=Mock()):
            return importlib.import_module("cattube.settings")


def import_apps():
    sys.modules.pop("cattube.core.apps", None)
    return importlib.import_module("cattube.core.apps")


class B2SettingsTests(unittest.TestCase):
    def test_standard_b2_env_configures_signed_storage_clients(self):
        settings = import_settings({
            "B2_APPLICATION_KEY_ID": "media-key-id",
            "B2_APPLICATION_KEY": "media-key",
            "B2_BUCKET_NAME": "media-bucket",
            "B2_REGION": "us-west-004",
            "B2_PUBLIC_URL_BASE": "https://media-bucket.s3.us-west-004.backblazeb2.com",
        })

        default_options = settings.STORAGES["default"]["OPTIONS"]
        static_options = settings.STORAGES["staticfiles"]["OPTIONS"]

        self.assertEqual(default_options["bucket_name"], "media-bucket")
        self.assertEqual(
            default_options["endpoint_url"],
            "https://s3.us-west-004.backblazeb2.com",
        )
        self.assertEqual(
            default_options["client_config"].user_agent_extra,
            "b2-twelvelabs-example (backblaze-b2-samples)",
        )
        self.assertEqual(static_options["bucket_name"], "media-bucket")
        self.assertNotIn("querystring_auth", static_options)
        self.assertEqual(static_options["location"], "static")

    def test_system_check_rejects_unsigned_static_urls_from_media_bucket(self):
        import_settings({
            "B2_APPLICATION_KEY_ID": "media-key-id",
            "B2_APPLICATION_KEY": "media-key",
            "B2_BUCKET_NAME": "media-bucket",
            "B2_REGION": "us-west-004",
            "B2_PUBLIC_URL_BASE": "https://media-bucket.s3.us-west-004.backblazeb2.com",
        })
        apps = import_apps()
        storages = {
            "default": {"OPTIONS": {"bucket_name": "media-bucket"}},
            "staticfiles": {
                "OPTIONS": {
                    "bucket_name": "media-bucket",
                    "querystring_auth": False,
                },
            },
        }

        with patch.object(apps, "settings", Mock(STORAGES=storages)):
            errors = apps.check_b2_storage_configuration(None)

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, "cattube.E001")

    def test_legacy_env_fallback_preserves_existing_prefixes_and_static_bucket(self):
        settings = import_settings({
            "DEFAULT_ACCESS_KEY_ID": "media-key-id",
            "DEFAULT_SECRET_ACCESS_KEY": "media-key",
            "DEFAULT_STORAGE_BUCKET_NAME": "media-bucket",
            "DEFAULT_S3_REGION_NAME": "us-west-004",
            "DEFAULT_STORAGE_LOCATION": "existing-media-prefix",
            "STATIC_ACCESS_KEY_ID": "static-key-id",
            "STATIC_SECRET_ACCESS_KEY": "static-key",
            "STATIC_STORAGE_BUCKET_NAME": "static-bucket",
            "STATIC_S3_REGION_NAME": "us-east-005",
            "STATIC_STORAGE_LOCATION": "existing-static-prefix",
        })

        default_options = settings.STORAGES["default"]["OPTIONS"]
        static_options = settings.STORAGES["staticfiles"]["OPTIONS"]

        self.assertEqual(default_options["access_key"], "media-key-id")
        self.assertEqual(default_options["bucket_name"], "media-bucket")
        self.assertEqual(default_options["location"], "existing-media-prefix")
        self.assertEqual(static_options["access_key"], "static-key-id")
        self.assertEqual(static_options["bucket_name"], "static-bucket")
        self.assertEqual(static_options["region_name"], "us-east-005")
        self.assertEqual(static_options["location"], "existing-static-prefix")
        self.assertEqual(
            settings.B2_PUBLIC_URL_BASE,
            "https://static-bucket.s3.us-east-005.backblazeb2.com",
        )

    def test_missing_required_b2_env_names_raise_clear_error(self):
        with self.assertRaisesRegex(
            ImproperlyConfigured,
            "B2_APPLICATION_KEY_ID, DEFAULT_ACCESS_KEY_ID",
        ):
            import_settings({})

    def test_public_url_base_rejects_unsafe_static_origins(self):
        unsafe_urls = [
            "http://media-bucket.s3.us-west-004.backblazeb2.com",
            "https://media-bucket@evil.example",
            "https://evil.example",
            "https://media-bucket.s3.us-west-004.backblazeb2.com?x=1",
            "https://media-bucket.s3.us-west-004.backblazeb2.com/#fragment",
        ]

        for unsafe_url in unsafe_urls:
            with self.subTest(unsafe_url=unsafe_url):
                with self.assertRaises(ImproperlyConfigured):
                    import_settings({
                        "B2_APPLICATION_KEY_ID": "media-key-id",
                        "B2_APPLICATION_KEY": "media-key",
                        "B2_BUCKET_NAME": "media-bucket",
                        "B2_REGION": "us-west-004",
                        "B2_PUBLIC_URL_BASE": unsafe_url,
                    })


if __name__ == "__main__":
    unittest.main()
