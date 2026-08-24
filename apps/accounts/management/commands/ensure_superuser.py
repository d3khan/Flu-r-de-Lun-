"""
Ensure the environment-configured superuser exists.

Replaces a bare ``createsuperuser --noinput`` in deploy build commands:

- Idempotent: safe on every build; skips when everything already matches.
- Matches users by EMAIL first (this project logs in by email:
  ``USERNAME_FIELD = 'email'``), falling back to username.
- Reads DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD (same variables
  ``createsuperuser`` uses), plus optional DJANGO_SUPERUSER_FIRST_NAME and
  DJANGO_SUPERUSER_LAST_NAME which stock ``createsuperuser`` cannot set.
- When the user already exists, keeps flags/name in sync with the env and
  re-syncs the password so the .env file stays the single source of truth.
  Set DJANGO_SUPERUSER_KEEP_PASSWORD=true to stop password re-syncs.
- Never raises: missing variables simply skip the command, so builds do not
  need ``|| true``, and any unexpected integrity problem is reported without
  failing the deploy.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError


class Command(BaseCommand):
    help = "Create or update the env-configured superuser (idempotent)."

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        first_name = os.environ.get("DJANGO_SUPERUSER_FIRST_NAME", "").strip()
        last_name = os.environ.get("DJANGO_SUPERUSER_LAST_NAME", "").strip()

        if not (email and password):
            self.stdout.write(
                "ensure_superuser: DJANGO_SUPERUSER_EMAIL/PASSWORD not fully "
                "set - skipping."
            )
            return

        # Login is by email here, so email identifies the account best.
        user = User.objects.filter(email__iexact=email).first()
        if user is None and username:
            user = User.objects.filter(username=username).first()

        if user is None:
            final_username = self._free_username(User, username or email.split("@")[0])
            try:
                user = User.objects.create_user(
                    username=final_username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                )
            except IntegrityError as exc:
                self.stdout.write(self.style.WARNING(
                    f"ensure_superuser: could not create superuser ({exc}) - skipping."
                ))
                return
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["is_staff", "is_superuser"])
            self.stdout.write(self.style.SUCCESS(
                f"ensure_superuser: created superuser '{final_username}' <{email}>."
            ))
            return

        changed = []

        if not (user.is_staff and user.is_superuser):
            user.is_staff = True
            user.is_superuser = True
            changed.append("flags")

        if first_name and user.first_name != first_name:
            user.first_name = first_name
            changed.append("first_name")

        if last_name and user.last_name != last_name:
            user.last_name = last_name
            changed.append("last_name")

        keep_password = os.environ.get(
            "DJANGO_SUPERUSER_KEEP_PASSWORD", ""
        ).lower() in ("1", "true", "yes")
        if (
            password
            and not keep_password
            and not user.check_password(password)
        ):
            user.set_password(password)
            changed.append("password")

        if changed:
            try:
                user.save()
            except IntegrityError as exc:
                self.stdout.write(self.style.WARNING(
                    f"ensure_superuser: could not update superuser ({exc}) - skipping."
                ))
                return
            self.stdout.write(self.style.WARNING(
                f"ensure_superuser: superuser '{user.username}' updated "
                f"({', '.join(changed)})."
            ))
        else:
            self.stdout.write(
                f"ensure_superuser: superuser '{user.username}' already up to date."
            )

    def _free_username(self, User, desired):
        """Return `desired`, or the first available `desired-2`, `-3`, ..."""
        candidate = desired[:150] or "admin"
        suffix = 2
        while User.objects.filter(username=candidate).exists():
            candidate = f"{desired[:147]}-{suffix}"
            suffix += 1
        return candidate
