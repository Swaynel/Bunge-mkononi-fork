from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("legislative", "0006_outboundmessage_webhookreceipt_subscription_cadence_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="outboundmessage",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("sending", "Sending"),
                    ("accepted", "Accepted"),
                    ("sent", "Sent"),
                    ("failed", "Failed"),
                    ("undelivered", "Undelivered"),
                    ("skipped", "Skipped"),
                ],
                default="queued",
                max_length=16,
            ),
        ),
    ]
