import uuid
from django.db import models
from django.contrib.auth import get_user_model


class Reports(models.Model):
    task_id = models.CharField(max_length=36)
    rept_name = models.CharField(max_length=255, blank=False)
    rept_type = models.CharField(max_length=12)
    status = models.CharField(max_length=12)
    created = models.DateTimeField()
    completed = models.IntegerField(default=0)
    perc_complete = models.IntegerField(default=0)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, blank=True, editable=False)
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True, editable=False)

    def __str__(self):
        return self.task_id