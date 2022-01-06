from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def clash_validator(value):
    if value != "":
        if value[0] != "#":
            raise ValidationError(
                _("Clash Royale id's must start with a #"),
                params={'value': value},
            )


class ClashField(models.CharField):
    def to_python(self, value):
        return value.upper()



class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    clash_id = ClashField(max_length=10, blank=True, validators=[clash_validator])
    clan_id = ClashField(max_length=9, blank=True, default='#YP8GPGYQ', validators=[clash_validator])

    def __str__(self):
        return f'{self.user.username} Profile'

    def save(self, *args, **kwargs):
        super(Profile, self).save(*args, **kwargs)


