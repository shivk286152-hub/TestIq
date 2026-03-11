# Generated manually to add missing fields to MockTest

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0002_alter_mocktest_difficulty_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='mocktest',
            name='difficulty',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('Beginner', 'Beginner'),
                    ('Intermediate', 'Intermediate'),
                    ('Advanced', 'Advanced')
                ],
                default='Intermediate',
            ),
        ),
        migrations.AddField(
            model_name='mocktest',
            name='negative_marking_type',
            field=models.CharField(
                max_length=25,
                choices=[
                    ('no_negative', 'No Negative Marking'),
                    ('fixed_per_question', 'Fixed per Wrong Question'),
                    ('percentage_of_marks', 'Percentage of Question Marks')
                ],
                default='no_negative',
            ),
        ),
        migrations.AddField(
            model_name='mocktest',
            name='negative_marking_value',
            field=models.FloatField(
                default=0,
                blank=True,
                help_text="Negative marks or percentage depending on type",
            ),
        ),
        migrations.AddField(
            model_name='mocktest',
            name='time_limit',
            field=models.PositiveIntegerField(
                default=30,
                help_text="Time limit per attempt in minutes",
            ),
        ),
        migrations.AddField(
            model_name='mocktest',
            name='total_marks',
            field=models.FloatField(default=0),
        ),
    ]