from django.db import models
from django.utils import timezone

class Gender(models.Model):
    gender = models.CharField(max_length=50)
    icon   = models.CharField(max_length=50, default='bi-gender-ambiguous')
    color  = models.CharField(max_length=20, default='#c4b5fd')

    def __str__(self):
        return self.gender

class AssignmentLocation(models.Model):
    name       = models.CharField(max_length=100)
    badge_color= models.CharField(max_length=20, default="badge-office-hq")
    icon       = models.CharField(max_length=50, default='bi-geo-alt-fill')

    def __str__(self):
        return self.name

class EmployeeRole(models.Model):
    name  = models.CharField(max_length=100)
    icon  = models.CharField(max_length=50, default='bi-briefcase-fill')
    color = models.CharField(max_length=20, default='#3d7fff')

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    username = models.CharField(max_length=150, unique=True) # Automated Employee ID
    employee_name = models.CharField(max_length=200, default="")
    birthday = models.DateField(null=True, blank=True)
    age = models.IntegerField(default=18)
    gender = models.ForeignKey(Gender, on_delete=models.CASCADE)
    email = models.EmailField(unique=True)
    address = models.TextField(default="")

    assignment_rel = models.ForeignKey(AssignmentLocation, on_delete=models.SET_NULL, null=True, blank=True)
    role_rel       = models.ForeignKey(EmployeeRole,       on_delete=models.SET_NULL, null=True, blank=True)

    password    = models.CharField(max_length=255)
    profile_pic = models.ImageField(upload_to='profiles/', null=True, blank=True)

    # Core Status Flags
    is_active  = models.BooleanField(default=True)
    is_on_duty = models.BooleanField(default=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee_name}"

class ActivityLog(models.Model):
    action    = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} at {self.timestamp}"



# ═══ ADMIN REGISTRATION + FACE ID + ADMIN PANEL (added) ═══
class AdminOTP(models.Model):
    code_hash  = models.CharField(max_length=128)
    purpose    = models.CharField(max_length=10, default='register')   # 'register' or 'panel'
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used    = models.BooleanField(default=False)
    attempts   = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"OTP #{self.id} {self.purpose} ({'used' if self.is_used else 'open'})"


class AdminRegistrationRequest(models.Model):
    STATUS = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]

    full_name     = models.CharField(max_length=200)
    employee_id   = models.CharField(max_length=50)
    age           = models.PositiveSmallIntegerField()
    location      = models.CharField(max_length=255)
    email         = models.EmailField()
    username      = models.CharField(max_length=150)
    password_hash = models.CharField(max_length=255)
    face_descriptor = models.TextField()                 # 128 numbers (JSON) used for matching
    face_photo    = models.TextField(blank=True, default='')   # small JPEG snapshot so approvers can SEE the applicant
    token         = models.CharField(max_length=64, unique=True)
    status        = models.CharField(max_length=10, choices=STATUS, default='pending')
    created_at    = models.DateTimeField(auto_now_add=True)
    reviewed_at   = models.DateTimeField(null=True, blank=True)
    reviewed_by   = models.CharField(max_length=150, blank=True, default='')
    user          = models.OneToOneField('auth.User', null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.full_name} ({self.status})"


class AdminFace(models.Model):
    user       = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='face')
    descriptor = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Face of {self.user.username}"
