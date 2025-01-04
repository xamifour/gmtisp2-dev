# mpi_src/appshere/accounts/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Organization, Nas
from django_recaptcha.fields import ReCaptchaField

# Sign-Up Form
class SignUpForm(UserCreationForm):
    captcha = ReCaptchaField()
    class Meta:
        model = User
        fields = ['username', 'name', 'password1', 'password2', 'captcha']  # Adjust the fields as per your model

# Sign-In Form (Inherits from AuthenticationForm)
class SignInForm(AuthenticationForm):
    captcha = ReCaptchaField()
    # captcha = ReCaptchaField(
    #     public_key='6LeXdXAqAAAAAK6SdXVnFCGBb3piEIR5F_2VMY1D',
    #     private_key='6LeXdXAqAAAAAFlqN7YzzSkU8NYphRQz3hNzFIoO',
    # )
    class Meta:
        model = User
        fields = ['username', 'password', 'captcha']


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = '__all__'
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 5}),
        }

class NasForm(forms.ModelForm):
    class Meta:
        model = Nas
        fields = '__all__'
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 5}),
        }