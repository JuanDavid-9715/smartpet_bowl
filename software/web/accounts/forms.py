from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(label="Correo", required=True)
    house_name = forms.CharField(label="Nombre de la casa", max_length=120, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            user.profile.house_name = self.cleaned_data.get("house_name", "")
            user.profile.save()
        return user


class EmailLoginForm(AuthenticationForm):
    username = forms.CharField(label="Correo o usuario")
