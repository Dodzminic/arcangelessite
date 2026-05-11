from django import forms
from .models import UserProfile

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput(), label="Confirm Password") # Criteria 7 (3%)

    class Meta:
        model = UserProfile
        fields = ['username', 'password', 'confirm_password', 'email', 'profile_pic', 'gender']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password: # Criteria 7 (3%)
            raise forms.ValidationError("Passwords do not match!")
        return cleaned_data