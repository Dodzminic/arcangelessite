from django.db import models

class Gender(models.Model):
    gender = models.CharField(max_length=100)
    def __str__(self):
        return self.gender

class UserProfile(models.Model):
    username = models.CharField(max_length=100, unique=True) # Criteria 6 (3%)
    password = models.CharField(max_length=100)
    email = models.EmailField()
    profile_pic = models.ImageField(upload_to='profiles/', null=True, blank=True) # Criteria 2 (25%)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE)

    def __str__(self):
        return self.username