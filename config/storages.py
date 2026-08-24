"""
Custom storages.

Kept separate from settings so they can be referenced by dotted path in the
STORAGES setting.
"""
from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStorage(CompressedManifestStaticFilesStorage):
    """WhiteNoise manifest storage that never crashes on missing entries.

    ``manifest_strict`` is a class attribute on Django's ManifestFilesMixin,
    not a constructor argument, so it cannot be set via the STORAGES
    ``OPTIONS`` dict. With it disabled, files absent from the manifest fall
    back to their plain (unhashed) URL instead of raising ValueError —
    protecting first-boot requests before ``collectstatic`` has produced a
    fresh manifest.
    """

    manifest_strict = False
