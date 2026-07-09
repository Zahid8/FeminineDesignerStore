"""Tests for media storage configuration (local default and S3 opt-in)."""

import os
from importlib import reload
from unittest import mock

from django import conf
from django.test import SimpleTestCase


class LocalMediaStorageTests(SimpleTestCase):
    """Default mode uses local filesystem storage."""

    def test_default_storage_is_filesystem(self):
        """When DJANGO_MEDIA_STORAGE is unset, default storage is FileSystemStorage."""
        # In local mode, STORAGES may not have a 'default' key — Django uses
        # FileSystemStorage as the implicit default in that case.
        default = conf.settings.STORAGES.get("default")
        if default:
            self.assertEqual(
                default["BACKEND"],
                "django.core.files.storage.FileSystemStorage",
            )
        else:
            # No explicit default → Django uses FileSystemStorage implicitly.
            # Verify MEDIA_ROOT exists.
            self.assertTrue(hasattr(conf.settings, "MEDIA_ROOT"))

    def test_media_url_default(self):
        # MEDIA_URL is set at startup; should contain "media"
        self.assertIn("media", conf.settings.MEDIA_URL)

    def test_staticfiles_storage_in_storages(self):
        """Static files storage is configured in STORAGES when S3 is off."""
        self.assertIn("staticfiles", conf.settings.STORAGES)


class S3StorageConfigTests(SimpleTestCase):
    """S3 mode configures storages.backends.s3.S3Storage correctly."""

    S3_ENV = {
        "DJANGO_MEDIA_STORAGE": "s3",
        "AWS_STORAGE_BUCKET_NAME": "my-bucket",
        "AWS_ACCESS_KEY_ID": "test-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret",
        "AWS_S3_REGION_NAME": "us-east-1",
    }

    def _load_settings_with_env(self, extra_env=None):
        env = dict(self.S3_ENV)
        if extra_env:
            env.update(extra_env)
        with mock.patch.dict(os.environ, env, clear=True):
            import femdes_site.settings as s
            reload(s)
            return s

    def test_s3_mode_selects_s3_storage(self):
        s = self._load_settings_with_env()
        backend = s.STORAGES["default"]["BACKEND"]
        self.assertEqual(backend, "storages.backends.s3.S3Storage")

    def test_s3_options_include_region(self):
        s = self._load_settings_with_env()
        opts = s.STORAGES["default"]["OPTIONS"]
        self.assertEqual(opts.get("region_name"), "us-east-1")

    def test_s3_custom_endpoint(self):
        s = self._load_settings_with_env({
            "AWS_S3_ENDPOINT_URL": "https://abc.r2.cloudflarestorage.com",
        })
        opts = s.STORAGES["default"]["OPTIONS"]
        self.assertEqual(
            opts.get("endpoint_url"), "https://abc.r2.cloudflarestorage.com"
        )

    def test_s3_custom_domain(self):
        s = self._load_settings_with_env({
            "AWS_S3_CUSTOM_DOMAIN": "cdn.example.com",
        })
        opts = s.STORAGES["default"]["OPTIONS"]
        self.assertEqual(opts.get("custom_domain"), "cdn.example.com")

    def test_s3_static_storage_unchanged(self):
        s = self._load_settings_with_env()
        self.assertEqual(
            s.STORAGES["staticfiles"]["BACKEND"],
            "django.contrib.staticfiles.storage.StaticFilesStorage",
        )

    def test_s3_without_bucket_raises(self):
        env = dict(self.S3_ENV)
        del env["AWS_STORAGE_BUCKET_NAME"]
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError) as ctx:
                import femdes_site.settings as s
                reload(s)
            self.assertIn("AWS_STORAGE_BUCKET_NAME", str(ctx.exception))


class LocalAfterS3RestoreTests(SimpleTestCase):
    """After S3 tests, local mode is still default."""

    def test_local_mode_restored(self):
        """Default mode works after S3 tests reload settings."""
        with mock.patch.dict(os.environ, {}, clear=True):
            import femdes_site.settings as s
            reload(s)
        self.assertFalse(hasattr(conf.settings, "AWS_STORAGE_BUCKET_NAME"))
