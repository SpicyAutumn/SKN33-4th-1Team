from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm

from .models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(label="이메일")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")
        labels = {"username": "아이디"}
        help_texts = {"username": "영문, 숫자, @/./+/-/_만 사용할 수 있습니다."}


class LoginForm(forms.Form):
    identifier = forms.CharField(label="아이디 또는 이메일", max_length=254)
    password = forms.CharField(label="비밀번호", widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get("identifier")
        password = cleaned_data.get("password")
        if identifier and password:
            self.user_cache = authenticate(self.request, username=identifier, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("아이디 또는 이메일, 비밀번호를 다시 확인해 주세요.")
        return cleaned_data

    def get_user(self):
        return self.user_cache
