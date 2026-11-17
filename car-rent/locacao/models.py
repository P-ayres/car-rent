from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction

# Create your models here.

SEXO_CHOICES = [
    ('M', 'Masculino'),
    ('F', 'Feminino'),
    ('O', "Outro"),
    ('N', "Não Informar"),
]

CATEGORIA_CHOICES = [
    ('E', 'Economico'),
    ('C', 'Compacto'),
    ('M', 'Medio'),
    ('S', 'SUV'),
    ('L', 'Luxo'),
]

TIPO_MANUTENCAO_CHOICES = [
    ('P', 'Preventiva'),
    ('C', 'Corretiva'),
]

STATUS_CHOICES = [
    ('D', 'Disponível'),
    ('I', 'Indisponível'),
    ('M', 'Em manutenção'),
    ('R', 'Reservado'),
]

STATUS_RESERVA = [
    ('P', 'Pendente'),
    ('A', 'Em andamento'),
    ('C', 'Concluída'),
    ('X', 'Cancelada'),
]


class Funcionario(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='funcionario',
    )
    nome = models.CharField(max_length=100)
    sobrenome = models.CharField(max_length=100)
    cargo = models.CharField(max_length=100, default='')
    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES)
    ativo = models.BooleanField(default=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    isAdmin = models.BooleanField(default=False)

    def __str__(self):
        return self.nome + " " + self.sobrenome

    def save(self, *args, **kwargs):
        self.nome = self.nome.title()
        self.sobrenome = self.sobrenome.title()

        super().save(*args, **kwargs)


class Veiculo(models.Model):
    modelo = models.CharField(max_length=100)
    placa = models.CharField(max_length=10, unique=True)
    categoria = models.CharField(max_length=1, choices=CATEGORIA_CHOICES)
    status = models.CharField(
        max_length=1, choices=STATUS_CHOICES, default='D')
    preco_locacao = models.DecimalField(max_digits=10, decimal_places=2)
    marca = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.marca} {self.modelo} ({self.placa})"


class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    sobrenome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    cnpj = models.CharField(max_length=18, unique=True, null=True, blank=True)
    endereco = models.CharField(max_length=200, default='')
    telefone = models.CharField(max_length=20, default='')
    data_cadastro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome + " " + self.sobrenome

    def save(self, *args, **kwargs):
        self.nome = self.nome.title()
        self.sobrenome = self.sobrenome.title()

        super().save(*args, **kwargs)


class Reserva(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    veiculo = models.ForeignKey(Veiculo, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=1,
        choices=STATUS_RESERVA,
        default='P',
    )
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    data_cadastro = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas',
    )

    valor_locacao = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    valor_diaria = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)
    valor_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Reserva de {self.cliente} - {self.veiculo} ({self.data_inicio} a {self.data_fim})"

    @staticmethod
    def calcular_dias(data_inicio, data_fim):

        periodo = data_fim - data_inicio
        dias = periodo.days
        if periodo % timedelta(days=1):
            dias += 1
        return max(dias, 1)

    @property
    def quantidade_dias(self):
        return self.calcular_dias(self.data_inicio, self.data_fim)

    def calcular_valor(self):

        tarifa = Tarifa.objects.get(categoria=self.veiculo.categoria)
        self.valor_locacao = self.veiculo.preco_locacao
        self.valor_diaria = tarifa.valor_diaria
        self.valor_total = self.valor_locacao + \
            self.valor_diaria * self.quantidade_dias


class Manutencao(models.Model):
    veiculo = models.ForeignKey(
        Veiculo,
        on_delete=models.CASCADE,
        related_name='manutencoes',
    )
    tipo = models.CharField(max_length=1, choices=TIPO_MANUTENCAO_CHOICES)
    motivo = models.CharField(max_length=200)
    previsao_conclusao = models.DateField()
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.veiculo}"


class Tarifa(models.Model):
    categoria = models.CharField(
        max_length=1, choices=CATEGORIA_CHOICES, unique=True)
    valor_diaria = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.get_categoria_display()}: R$ {self.valor_diaria}/dia"


class Retirada(models.Model):
    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.CASCADE,
        related_name='retirada',
    )
    data_retirada = models.DateTimeField(auto_now_add=True)
    quilometragem_inicial = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    nivel_combustivel = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    def __str__(self):
        return f"Retirada de {self.reserva}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            return super().save(*args, **kwargs)

        with transaction.atomic():
            reserva = Reserva.objects.select_for_update().get(pk=self.reserva_id)
            veiculo = Veiculo.objects.select_for_update().get(pk=reserva.veiculo_id)
            if reserva.status != 'P' or veiculo.status != 'R':
                raise ValidationError(
                    'Somente reservas pendentes com veículo reservado podem ter retirada.'
                )

            super().save(*args, **kwargs)
            reserva.status = 'A'
            reserva.save(update_fields=['status'])
            veiculo.status = 'I'
            veiculo.save(update_fields=['status'])
            self.reserva = reserva


class Devolucao(models.Model):
    reserva = models.OneToOneField(
        Reserva,
        on_delete=models.CASCADE,
        related_name='devolucao',
    )
    data_devolucao = models.DateTimeField(auto_now_add=True)
    quilometragem_final = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    danos = models.BooleanField(default=False)
    descricao_danos = models.TextField(blank=True)
    multa_atraso = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    multa_danos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    @property
    def valor_multa_total(self):
        return self.multa_atraso + self.multa_danos

    @property
    def valor_final(self):
        return self.reserva.valor_total + self.valor_multa_total

    def __str__(self):
        return f"Devolução de {self.reserva}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            return super().save(*args, **kwargs)

        with transaction.atomic():
            reserva = Reserva.objects.select_for_update().get(pk=self.reserva_id)
            veiculo = Veiculo.objects.select_for_update().get(pk=reserva.veiculo_id)
            if (reserva.status != 'A'
                    or not Retirada.objects.filter(reserva=reserva).exists()):
                raise ValidationError(
                    'Somente reservas em andamento com retirada registrada podem ter devolução.'
                )

            super().save(*args, **kwargs)
            reserva.status = 'C'
            reserva.save(update_fields=['status'])
            veiculo.status = 'D'
            veiculo.save(update_fields=['status'])
            self.reserva = reserva
