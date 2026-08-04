import re

from django.db import migrations, models


def canonical_phone(value):
    digits = re.sub(r"\D", "", str(value or ""))

    if len(digits) == 10 and digits.startswith("07"):
        return f"+256{digits[1:]}"
    if len(digits) == 12 and digits.startswith("2567"):
        return f"+{digits}"
    if len(digits) == 9 and digits.startswith("7"):
        return f"+256{digits}"
    return None


def normalize_and_deduplicate(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    UserProfile = apps.get_model("accounts", "UserProfile")
    primary_numbers = set(
        User.objects.exclude(phone__isnull=True).values_list("phone", flat=True)
    )
    used = set()

    for profile in UserProfile.objects.order_by("created_at", "pk").iterator():
        normalized = canonical_phone(profile.alternative_phone)
        if normalized in primary_numbers or normalized in used:
            normalized = None
        if normalized:
            used.add(normalized)
        if profile.alternative_phone != normalized:
            UserProfile.objects.filter(pk=profile.pk).update(
                alternative_phone=normalized
            )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0015_user_sessions_and_alternative_phone"),
    ]

    operations = [
        migrations.RunPython(
            normalize_and_deduplicate,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="userprofile",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(alternative_phone__isnull=True)
                    | models.Q(alternative_phone__regex=r"^\+2567[0-9]{8}$")
                ),
                name="acct_profile_alt_phone_ug",
            ),
        ),
        migrations.AddConstraint(
            model_name="userprofile",
            constraint=models.UniqueConstraint(
                fields=("alternative_phone",),
                condition=models.Q(alternative_phone__isnull=False),
                name="acct_profile_alt_phone_uniq",
            ),
        ),
    ]
