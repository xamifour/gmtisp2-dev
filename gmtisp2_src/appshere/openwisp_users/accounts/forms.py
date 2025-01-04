# # from allauth.account.forms import LoginForm, SignupForm
# # from captcha.fields import ReCaptchaField
# # from captcha.widgets import ReCaptchaV2Checkbox

# # class CustomLoginForm(LoginForm):
# #     captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

# #     def clean(self):
# #         cleaned_data = super().clean()
# #         return cleaned_data


# # class CustomSignupForm(SignupForm):
# #     captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

# #     def clean(self):
# #         cleaned_data = super().clean()
# #         return cleaned_data


# from allauth.account.forms import LoginForm, SignupForm
# from captcha.fields import ReCaptchaField
# from captcha.widgets import ReCaptchaV2Checkbox

# # Custom Signup Form with reCAPTCHA
# class CustomSignupForm(SignupForm):
#     captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)

# # Custom Login Form with reCAPTCHA
# class CustomLoginForm(LoginForm):
#     captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)
