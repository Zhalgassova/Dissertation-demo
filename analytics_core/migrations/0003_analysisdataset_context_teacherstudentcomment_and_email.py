from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('analytics_core', '0002_analysisdataset_performancerecord'),
    ]

    operations = [
        migrations.AddField(
            model_name='analysisdataset',
            name='cohort_label',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='analysisdataset',
            name='subject_title',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name='analysisdataset',
            name='teacher_name',
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name='performancerecord',
            name='student_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.CreateModel(
            name='TeacherStudentComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_name', models.CharField(max_length=180)),
                ('student_email', models.EmailField(blank=True, max_length=254)),
                ('group_name', models.CharField(blank=True, max_length=120)),
                ('comment', models.TextField(blank=True)),
                ('dataset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teacher_comments', to='analytics_core.analysisdataset')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_comments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['student_name'],
                'unique_together': {('dataset', 'teacher', 'student_name')},
            },
        ),
    ]
