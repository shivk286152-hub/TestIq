# exams/migrations/0003_fix_duplicate_options.py
from django.db import migrations

def fix_duplicate_options(apps, schema_editor):
    Option = apps.get_model('exams', 'Option')
    
    # Find duplicates for question_id=1 with order=0
    duplicates = Option.objects.filter(question_id=1, order=0)
    
    if duplicates.count() > 1:
        # Keep the first one, delete others
        first = duplicates.first()
        duplicates.exclude(id=first.id).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('exams', '0002_alter_mocktestattempt_options_and_more'),  # Adjust based on your actual last migration
    ]
    
    operations = [
        migrations.RunPython(fix_duplicate_options),
      ]
