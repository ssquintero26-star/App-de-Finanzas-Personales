from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0016_account_created_at_account_updated_at_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name=model_name,
            name=field_name,
            field=models.DateTimeField(**options),
            preserve_default=False,
        )
        for model_name, field_name, options in [
            (
                "transaction", "created_at",
                {"auto_now_add": True, "default": timezone.now},
            ),
            ("transaction", "updated_at", {"auto_now": True}),
            (
                "sharedexpenseparticipant", "created_at",
                {"auto_now_add": True, "default": timezone.now},
            ),
            ("sharedexpenseparticipant", "updated_at", {"auto_now": True}),
            (
                "sharedexpensepayment", "created_at",
                {"auto_now_add": True, "default": timezone.now},
            ),
        ]
    ]
