from django.db import models
from django.utils import timezone

class Gender(models.Model):
    gender = models.CharField(max_length=50)

    def __str__(self):
        return self.gender

class AssignmentLocation(models.Model):
    name = models.CharField(max_length=100)
    badge_color = models.CharField(max_length=20, default="badge-office-hq")

    def __str__(self):
        return self.name

class EmployeeRole(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    username = models.CharField(max_length=150, unique=True) # Automated Employee ID
    employee_name = models.CharField(max_length=200, default="")
    age = models.IntegerField(default=18)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE)
    email = models.EmailField(unique=True)
    address = models.TextField(default="")
    
    assignment_rel = models.ForeignKey(AssignmentLocation, on_delete=models.SET_NULL, null=True, blank=True)
    role_rel = models.ForeignKey(EmployeeRole, on_delete=models.SET_NULL, null=True, blank=True)
    
    password = models.CharField(max_length=255)
    profile_pic = models.ImageField(upload_to='profiles/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee_name}"

class ActivityLog(models.Model):
    action = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} at {self.timestamp}"