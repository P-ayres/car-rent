from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from .models import (
    CATEGORIA_CHOICES,
    Cliente,
    Devolucao,
    Funcionario,
    Manutencao,
    Retirada,
    Tarifa,
    Veiculo,
    Reserva,
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


class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = [
            'cliente',
            'veiculo',
            'data_inicio',
            'data_fim',
        ]

        labels = {
            'data_inicio': 'Data de retirada',
            'data_fim': 'Data de devolução',
        }

        widgets = {
            'cliente': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Selecione o cliente'
            }),
            'veiculo': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Selecione o veículo'
            }),
            'data_inicio': forms.DateInput(attrs={
                'class': 'form-control',
                'placeholder': 'dd/mm/aaaa'
            }),
            'data_fim': forms.DateInput(attrs={
                'class': 'form-control',
                'placeholder': 'dd/mm/aaaa'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['veiculo'].queryset = Veiculo.objects.filter(
            status='D').order_by(Lower('modelo'))
        self.fields['veiculo'].label_from_instance = (
            lambda obj: f'{obj.modelo} - {obj.placa} ({obj.get_categoria_display()})')
        if self.instance.pk:
            # Na edição pode trocar o carro: lista o atual + os disponíveis.
            # O cliente continua travado (o Django ignora o valor do POST).
            self.fields['veiculo'].queryset = Veiculo.objects.filter(
                Q(status='D') | Q(pk=self.instance.veiculo_id)
            ).order_by(Lower('modelo'))
            self.fields['cliente'].disabled = True

    CAMPOS_DO_VALOR = {'veiculo', 'data_inicio', 'data_fim'}

    def precisa_calcular_valor(self):
        return (not self.instance.pk
                or bool(self.CAMPOS_DO_VALOR & set(self.changed_data)))

    def clean(self):
        cleaned_data = super().clean()
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')
        if data_inicio and data_fim and data_inicio >= data_fim:
            raise forms.ValidationError(
                'A data de retirada deve ser anterior à data de devolução.')

        veiculo = cleaned_data.get('veiculo')
        if (veiculo and self.precisa_calcular_valor()
                and not Tarifa.objects.filter(categoria=veiculo.categoria).exists()):
            self.add_error(
                'veiculo',
                f'Não há tarifa cadastrada para a categoria '
                f'{veiculo.get_categoria_display()}. '
                f'Configure as tarifas antes de reservar este veículo.',
            )
        return cleaned_data

    def save(self, commit=True):
        reserva = super().save(commit=False)
        if self.precisa_calcular_valor():
            reserva.calcular_valor()
        if commit:
            reserva.save()
        return reserva


class ManutencaoForm(forms.ModelForm):
    class Meta:
        model = Manutencao
        fields = [
            'veiculo',
            'tipo',
            'motivo',
            'previsao_conclusao',
            'custo',
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
        if not self.instance.pk:
            self.fields['custo'].widget = forms.HiddenInput()

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


class ConfirmarRetiradaForm(forms.ModelForm):
    class Meta:
        model = Retirada
        fields = [
            'quilometragem_inicial',
            'nivel_combustivel',
        ]
        labels = {
            'quilometragem_inicial': 'Quilometragem inicial (km)',
            'nivel_combustivel': 'Nível de combustível (litros)',
        }
        widgets = {
            'quilometragem_inicial': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': 1,
            }),
            'nivel_combustivel': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
            }),
        }


class ConfirmarDevolucaoForm(forms.ModelForm):
    multa_danos = forms.DecimalField(
        label='Multa por danos (R$)',
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0'),
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 0,
            'step': '0.01',
        }),
    )

    class Meta:
        model = Devolucao
        fields = [
            'quilometragem_final',
            'danos',
            'descricao_danos',
            'multa_danos',
        ]
        labels = {
            'quilometragem_final': 'Quilometragem final (km)',
            'danos': 'Há danos?',
            'descricao_danos': 'Descrição dos danos',
        }
        widgets = {
            'quilometragem_final': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
            }),
            'danos': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'descricao_danos': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descreva os danos identificados',
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        quilometragem = cleaned_data.get('quilometragem_final')

        if quilometragem is not None and self.instance.reserva_id:
            quilometragem_inicial = self.instance.reserva.retirada.quilometragem_inicial
            if quilometragem < quilometragem_inicial:
                self.add_error(
                    'quilometragem_final',
                    'A quilometragem final não pode ser menor que a inicial.',
                )

        tem_danos = cleaned_data.get('danos')
        descricao_danos = cleaned_data.get('descricao_danos')
        multa_danos = cleaned_data.get('multa_danos')

        if tem_danos and not descricao_danos:
            self.add_error('descricao_danos', 'Descreva os danos identificados.')

        if not tem_danos and (descricao_danos or multa_danos):
            raise forms.ValidationError(
                'Marque "Há danos?" para informar uma descrição ou multa por danos.'
            )

        if cleaned_data.get('multa_danos') is None and 'multa_danos' not in self.errors:
            cleaned_data['multa_danos'] = Decimal('0')

        return cleaned_data
