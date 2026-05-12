from django.db import models

class Gender(models.Model):
    gender = models.CharField(max_length=100)
    def __str__(self):
        return self.gender

class UserProfile(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255) # Long for hashing
    email = models.EmailField()
    profile_pic = models.ImageField(upload_to='profiles/', null=True, blank=True)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True) # Soft Delete
    created_at = models.DateTimeField(auto_now_add=True) # Audit Log

    def __str__(self):
        return self.username