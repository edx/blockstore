# By default django and many MySQL installations use a broken
# version of unicode ("utf8"). We should always use "utf8mb4"
# which is a correct/non-broken unicode character set, and fully
# supports characters in the supplementary multilingual plane,
# such as emoji, musical notation, mathematical alphanumerics,
# hieroglyphs, cuneiform, rare/historic language symbols
# (sometimes still used in asian family names), and more.
#
# Django has no supported way to change the character set and collation
# so we change it here in a migration.
# By specifying "run_before", we can force this to be the first migration.


from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    run_before = [
        ('contenttypes', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            'ALTER DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
