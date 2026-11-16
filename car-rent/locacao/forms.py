from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.db.models.functions import Lower
from django.utils import timezone

from .models import (
    CATEGORIA_CHOICES,
    Cliente,
    Funcionario,
    Manutencao,
    Tarifa,
    Veiculo,
)

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


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'nome',
            'sobrenome',
            'cpf',
            'cnpj',
            'endereco',
            'telefone',
        ]

        labels = {
            'cpf': 'CPF',
            'cnpj': 'CNPJ',
            'endereco': 'Endereço',
        }

        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'form-control text-red',
                'placeholder': 'Digite o nome do cliente'
            }),

            'sobrenome': forms.TextInput(attrs={
                'class': 'form-control text-red',
                'placeholder': 'Digite o sobrenome do cliente'

            }),

            'cpf': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o CPF do cliente'
            }),

            'cnpj': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o CNPJ do cliente'
            }),

            'endereco': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o endereço do cliente'
            }),

            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(00) 00000-0000'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('cpf') and not cleaned_data.get('cnpj'):
            raise forms.ValidationError('Informe o CPF ou o CNPJ do cliente.')
        return cleaned_data


class ManutencaoForm(forms.ModelForm):
    class Meta:
        model = Manutencao
        fields = [
            'veiculo',
            'tipo',
            'motivo',
            'previsao_conclusao',
        ]
        labels = {
            'veiculo': 'Veículo',
            'previsao_conclusao': 'Previsão de conclusão',
        }
        widgets = {
            'veiculo': forms.Select(attrs={
                'class': 'form-select',
            }),
            'tipo': forms.Select(attrs={
                'class': 'form-select',
            }),
            'motivo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o motivo da manutenção'
            }),
            'previsao_conclusao': forms.DateInput(attrs={
                'class': 'form-control',
                'placeholder': 'dd/mm/aaaa'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['veiculo'].queryset = Veiculo.objects.filter(
            status='D').order_by(Lower('modelo'))

    def clean_previsao_conclusao(self):
        previsao = self.cleaned_data['previsao_conclusao']
        if previsao < timezone.localdate():
            raise forms.ValidationError(
                'A previsão de conclusão não pode ser uma data passada.')
        return previsao


class TarifaForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        atuais = {t.categoria: t.valor_diaria for t in Tarifa.objects.all()}

        for codigo, nome in CATEGORIA_CHOICES:
            self.fields[f'categoria_{codigo}'] = forms.DecimalField(
                label=nome,
                max_digits=10,
                decimal_places=2,
                min_value=Decimal('0.01'),
                initial=atuais.get(codigo),
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'step': '0.01',
                    'placeholder': 'Valor da diária',
                }),
            )

    def campos_por_classe(self):
        for codigo, nome in CATEGORIA_CHOICES:
            yield nome, self[f'categoria_{codigo}']

    def save(self):
        for codigo, _ in CATEGORIA_CHOICES:
            Tarifa.objects.update_or_create(
                categoria=codigo,
                defaults={
                    'valor_diaria': self.cleaned_data[f'categoria_{codigo}']},
            )
