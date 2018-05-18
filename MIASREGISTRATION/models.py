from django.db import models

# Create your models here.

class MiasUser(models.Model):
	firstName = models.CharField(max_length = 50)
	lastName = models.CharField(max_length = 50)
	eMail = models.CharField(max_length = 50)
	password = models.CharField(max_length = 25)