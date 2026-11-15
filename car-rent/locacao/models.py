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
