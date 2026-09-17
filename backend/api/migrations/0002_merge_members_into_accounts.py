from django.db import migrations


def merge_members(apps, _schema_editor):
    Member = apps.get_model("api", "Member")
    from accounts.models import User

    for member in Member.objects.order_by("id"):
        if User.objects.filter(username=member.username).exists() or User.objects.filter(email=member.email).exists():
            raise RuntimeError("heritage_members 계정이 accounts_user와 충돌합니다.")
        User.objects.create(username=member.username, email=member.email, password=member.password)


class Migration(migrations.Migration):
    dependencies = [("api", "0001_initial")]

    operations = [
        migrations.RunPython(merge_members, migrations.RunPython.noop),
        migrations.DeleteModel(name="Member"),
    ]
