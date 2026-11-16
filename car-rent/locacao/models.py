from django.conf import settings
from django.db import models

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

    def __str__(self):
        return f"Reserva de {self.cliente} - {self.veiculo} ({self.data_inicio} a {self.data_fim})"


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
