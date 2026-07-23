import re

from django.db import IntegrityError, migrations, models, transaction


def canonical_phone(value):
    digits = re.sub(r"\D", "", str(value or ""))

    if digits.startswith("256"):
        national_number = digits[3:]
    elif digits.startswith("0"):
        national_number = digits[1:]
    else:
        national_number = digits

    if not re.fullmatch(r"7\d{8}", national_number):
        raise RuntimeError(f"Invalid Ugandan phone number in accounts_user: {value!r}")

    return f"+256{national_number}"


def survivor_score(user):
    """Prefer established, privileged, and verified accounts."""
    role_rank = {"user": 0, "moderator": 1, "admin": 2}
    return (
        bool(user.is_active),
        bool(user.is_superuser),
        bool(user.is_staff),
        role_rank.get(user.role, 0),
        bool(user.is_verified),
        bool(user.phone_verified_at),
        bool(user.email_verified_at),
        bool(user.last_login),
        bool(user.email),
        bool(user.google_sub),
        -user.id,
    )


def merge_profile(apps, database_alias, survivor_id, duplicate_id):
    UserProfile = apps.get_model("accounts", "UserProfile")
    survivor_profile = UserProfile.objects.using(database_alias).filter(
        user_id=survivor_id
    ).first()
    duplicate_profile = UserProfile.objects.using(database_alias).filter(
        user_id=duplicate_id
    ).first()

    if not duplicate_profile:
        return

    if not survivor_profile:
        UserProfile.objects.using(database_alias).filter(
            pk=duplicate_profile.pk
        ).update(user_id=survivor_id)
        return

    for field_name in (
        "avatar",
        "cover_photo",
        "default_city_id",
        "bio",
        "business_name",
    ):
        if not getattr(survivor_profile, field_name) and getattr(
            duplicate_profile, field_name
        ):
            setattr(
                survivor_profile,
                field_name,
                getattr(duplicate_profile, field_name),
            )

    duplicate_preferences = duplicate_profile.notification_preferences or {}
    survivor_preferences = survivor_profile.notification_preferences or {}
    survivor_profile.notification_preferences = {
        **duplicate_preferences,
        **survivor_preferences,
    }
    survivor_profile.trust_score = max(
        survivor_profile.trust_score,
        duplicate_profile.trust_score,
    )
    survivor_profile.total_listings = max(
        survivor_profile.total_listings,
        duplicate_profile.total_listings,
    )
    survivor_profile.save()
    duplicate_profile.delete()


def transfer_related_objects(apps, database_alias, survivor_id, duplicate_id):
    """Move direct user relations, dropping only rows that become duplicates."""
    User = apps.get_model("accounts", "User")
    UserProfile = apps.get_model("accounts", "UserProfile")
    related_models = {}

    for relation in User._meta.related_objects:
        related_model = relation.related_model
        if related_model == UserProfile:
            continue

        user_fields = [
            field
            for field in related_model._meta.fields
            if field.is_relation
            and field.remote_field
            and field.remote_field.model == User
        ]
        if user_fields:
            related_models[related_model] = user_fields

    for related_model, user_fields in related_models.items():
        duplicate_filter = models.Q()
        for field in user_fields:
            duplicate_filter |= models.Q(**{field.attname: duplicate_id})

        related_rows = list(
            related_model.objects.using(database_alias).filter(duplicate_filter)
        )
        for related_row in related_rows:
            updates = {
                field.attname: survivor_id
                for field in user_fields
                if getattr(related_row, field.attname) == duplicate_id
            }
            if not updates:
                continue

            resulting_user_ids = [
                updates.get(field.attname, getattr(related_row, field.attname))
                for field in user_fields
                if not field.null
            ]
            if len(resulting_user_ids) > 1 and len(set(resulting_user_ids)) == 1:
                related_row.delete()
                continue

            try:
                with transaction.atomic(using=database_alias):
                    related_model.objects.using(database_alias).filter(
                        pk=related_row.pk
                    ).update(**updates)
            except IntegrityError:
                # The survivor already owns the equivalent unique relation.
                related_row.delete()


def merged_user_values(survivor, duplicate):
    role_rank = {"user": 0, "moderator": 1, "admin": 2}
    role = max(
        (survivor.role, duplicate.role),
        key=lambda value: role_rank.get(value, 0),
    )

    values = {
        "full_name": survivor.full_name or duplicate.full_name,
        "role": role,
        "is_active": survivor.is_active or duplicate.is_active,
        "is_staff": survivor.is_staff or duplicate.is_staff,
        "is_superuser": survivor.is_superuser or duplicate.is_superuser,
        "is_verified": survivor.is_verified or duplicate.is_verified,
        "is_banned": survivor.is_banned and duplicate.is_banned,
        "last_login": max(
            filter(None, (survivor.last_login, duplicate.last_login)),
            default=None,
        ),
        "date_joined": min(survivor.date_joined, duplicate.date_joined),
        "phone_verified_at": max(
            filter(
                None,
                (survivor.phone_verified_at, duplicate.phone_verified_at),
            ),
            default=None,
        ),
        "email_verified_at": max(
            filter(
                None,
                (survivor.email_verified_at, duplicate.email_verified_at),
            ),
            default=None,
        ),
    }

    for field_name in ("email", "google_sub", "banned_reason"):
        values[field_name] = getattr(survivor, field_name) or getattr(
            duplicate, field_name
        )

    if not survivor.password or survivor.password.startswith("!"):
        values["password"] = duplicate.password

    return values


def merge_duplicate_users(apps, database_alias, users):
    User = apps.get_model("accounts", "User")
    survivor = max(users, key=survivor_score)

    for duplicate in users:
        if duplicate.pk == survivor.pk:
            continue

        merged_values = merged_user_values(survivor, duplicate)

        for field_name in ("groups", "user_permissions"):
            survivor_relation = getattr(survivor, field_name)
            duplicate_values = getattr(duplicate, field_name).all()
            survivor_relation.add(*duplicate_values)

        merge_profile(apps, database_alias, survivor.pk, duplicate.pk)
        transfer_related_objects(
            apps,
            database_alias,
            survivor.pk,
            duplicate.pk,
        )
        duplicate.delete()

        User.objects.using(database_alias).filter(pk=survivor.pk).update(
            **merged_values
        )
        survivor = User.objects.using(database_alias).get(pk=survivor.pk)

    return survivor


def normalize_existing_phones(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    database_alias = schema_editor.connection.alias
    normalized_groups = {}

    for user in User.objects.using(database_alias).all():
        if not user.phone:
            if user.phone == "":
                User.objects.using(database_alias).filter(pk=user.pk).update(
                    phone=None
                )
            continue

        normalized = canonical_phone(user.phone)
        normalized_groups.setdefault(normalized, []).append(user)

    for normalized, users in normalized_groups.items():
        if len(users) > 1:
            survivor = merge_duplicate_users(apps, database_alias, users)
        else:
            survivor = users[0]

        User.objects.using(database_alias).filter(pk=survivor.pk).update(
            phone=normalized
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_email_verification_status"),
    ]

    operations = [
        migrations.RunPython(
            normalize_existing_phones,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                check=(
                    models.Q(phone__isnull=True)
                    | models.Q(phone__regex=r"^\+2567[0-9]{8}$")
                ),
                name="accounts_user_phone_canonical_ug",
            ),
        ),
    ]
