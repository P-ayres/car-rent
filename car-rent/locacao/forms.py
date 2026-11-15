from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError

from .models import Funcionario, Veiculo

User = get_user_model()


class FuncionarioForm(forms.ModelForm):
    username = forms.CharField(label='Usuário', max_length=150)
    password1 = forms.CharField(
        label='Senha',
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label='Confirmar senha',
        widget=forms.PasswordInput,
    )

    class Meta:
        model = Funcionario
        fields = [
            'nome',
            'sobrenome',
            'cargo',
            'sexo',
            'isAdmin',
        ]

        labels = {
            'isAdmin': 'Marque se o funcionário é administrador',
        }

        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control text-red',
                'placeholder': 'Digite o nome do funcionário'
            }),

            'sobrenome': forms.TextInput(attrs={
                'class': 'form-control text-red',
                'placeholder': 'Digite o sobrenome do funcionário'

            }),

            'cargo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o cargo do funcionário'
            }),

            'sexo': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Selecione o sexo do funcionário'
            }),
            'isAdmin': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.user_id:
            self.fields['username'].initial = self.instance.user.username
            self.fields['password1'].required = False
            self.fields['password2'].required = False

    def clean_username(self):
        username = self.cleaned_data['username']
        users = User._default_manager.filter(username=username)
        if self.instance.user_id:
            users = users.exclude(pk=self.instance.user_id)
        if users.exists():
            raise forms.ValidationError('Este usuário já está cadastrado.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        if self.instance.user_id and not password1 and not password2:
            return cleaned_data

        if password1 != password2:
            self.add_error('password2', 'As senhas não conferem.')
            return cleaned_data

        if password1:
            user = User(username=cleaned_data.get('username'))
            try:
                password_validation.validate_password(password1, user=user)
            except ValidationError as error:
                self.add_error('password1', error)

        return cleaned_data


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = [
            'modelo',
            'placa',
            'categoria',
            'status',
            'preco_locacao',
            'marca',
        ]
        labels = {
            'preco_locacao': 'Preço de Locação',
        }
        widgets = {
            'modelo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o modelo do veículo'
            }),
            'placa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite a placa do veículo'
            }),
            'categoria': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Selecione a categoria do veículo'
            }),
            'preco_locacao': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o preço de locação'
            }),
            'marca': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite a marca do veículo'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Selecione o status do veículo'
            }),
        }
