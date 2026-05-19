from django import forms
from .models import UserProfile, Gender

class UserForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'cyber-input', 'placeholder': 'Enter password'}),
        label="Password"
    )
    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'cyber-input', 'placeholder': 'Confirm password'}),
        label="Confirm Password"
    )
    profile_pic = forms.ImageField(
        required=False, 
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = UserProfile
        fields = ['username', 'employee_name', 'age', 'gender', 'email', 'address', 'office_or_field', 'role', 'profile_pic']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'cyber-input'}),
            'employee_name': forms.TextInput(attrs={'class': 'cyber-input'}),
            'age': forms.NumberInput(attrs={'class': 'cyber-input'}),
            'gender': forms.Select(attrs={'class': 'cyber-input'}),
            'email': forms.EmailInput(attrs={'class': 'cyber-input'}),
            'address': forms.Textarea(attrs={'class': 'cyber-input', 'rows': 2}),
            'office_or_field': forms.Select(attrs={'class': 'cyber-input'}),
            'role': forms.Select(attrs={'class': 'cyber-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match!")
        return cleaned_data

class GenderForm(forms.ModelForm):
    class Meta:
        model = Gender
        fields = ['gender']
        widgets = {
            'gender': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'New gender option...'}),
        }