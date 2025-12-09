2# Generated manually to add HealthRecord model
from django.db import migrations, models
import django.db.models.deletion
import uuid
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('farms', '0001_initial'),
        ('flock_management', '0003_change_housed_in_to_protect'),
    ]

    operations = [
        migrations.CreateModel(
            name='HealthRecord',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('record_date', models.DateField(db_index=True)),
                ('record_type', models.CharField(max_length=50, default='Health Check')),
                ('outcome', models.CharField(max_length=100, blank=True)),
                ('follow_up_date', models.DateField(blank=True, null=True)),
                ('disease', models.CharField(max_length=200, blank=True)),
                ('diagnosis', models.CharField(max_length=200, blank=True)),
                ('symptoms', models.TextField(blank=True)),
                ('treatment_name', models.CharField(max_length=200, blank=True)),
                ('treatment_method', models.CharField(max_length=100, blank=True)),
                ('dosage', models.CharField(max_length=100, blank=True)),
                ('administering_person', models.CharField(max_length=100, blank=True)),
                ('vet_name', models.CharField(max_length=100, blank=True)),
                ('vet_license', models.CharField(max_length=100, blank=True)),
                ('birds_affected', models.PositiveIntegerField(default=0)),
                ('cost_ghs', models.DecimalField(default=0, max_digits=12, decimal_places=2, validators=[django.core.validators.MinValueValidator(0)])),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('farm', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='health_records', to='farms.farm')),
                ('flock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='health_records', to='flock_management.flock')),
            ],
            options={
                'db_table': 'health_records',
                'ordering': ['-record_date'],
            },
        ),
        migrations.AddIndex(
            model_name='healthrecord',
            index=models.Index(fields=['farm', 'record_date'], name='health_reco_farm_id_27b62f_idx'),
        ),
        migrations.AddIndex(
            model_name='healthrecord',
            index=models.Index(fields=['flock', 'record_date'], name='health_reco_flock_i_519e62_idx'),
        ),
        migrations.AddIndex(
            model_name='healthrecord',
            index=models.Index(fields=['record_type'], name='health_reco_record__d2acef_idx'),
        ),
    ]
