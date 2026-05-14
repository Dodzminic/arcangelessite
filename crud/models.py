from django.db import models

class Gender(models.Model):
    gender = models.CharField(max_length=50)

    def __str__(self):
        return self.gender

class UserProfile(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='profiles/', null=True, blank=True)
    is_active = models.BooleanField(default=True) # Soft Archive Toggle
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username