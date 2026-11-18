"""Popula o banco com dados de teste.

Uso:
    python manage.py popular_banco           # só roda se não houver clientes/veículos
    python manage.py popular_banco --limpar  # apaga os dados de teste e recria

Usuários criados (senha: teste123): ana.admin, bruno, carla, diego (inativo).
"""
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from locacao.models import (
    Cliente,
    Devolucao,
    Funcionario,
    Manutencao,
    Reserva,
    Retirada,
    Tarifa,
    Veiculo,
)

SENHA = 'teste123'

TARIFAS = {'E': '89.90', 'C': '119.90', 'M': '159.90', 'S': '229.90', 'L': '449.90'}

FUNCIONARIOS = [
    # username, nome, sobrenome, cargo, sexo, admin, ativo
    ('ana.admin', 'Ana', 'Ribeiro', 'Gerente', 'F', True, True),
    ('bruno', 'Bruno', 'Martins', 'Atendente', 'M', False, True),
    ('carla', 'Carla', 'Souza', 'Atendente', 'F', False, True),
    ('diego', 'Diego', 'Almeida', 'Manobrista', 'M', False, False),
]

CLIENTES = [
    ('João', 'Silva', '123.456.789-01', None, 'Rua das Flores, 120 - Porto Alegre', '(51) 99812-3344'),
    ('Maria', 'Oliveira', '234.567.890-12', None, 'Av. Ipiranga, 4500 - Porto Alegre', '(51) 99733-1122'),
    ('Pedro', 'Santos', '345.678.901-23', None, 'Rua Padre Chagas, 77 - Porto Alegre', '(51) 98455-0091'),
    ('Juliana', 'Costa', '456.789.012-34', None, 'Rua 24 de Outubro, 310 - Porto Alegre', '(51) 99102-7788'),
    ('Lucas', 'Pereira', '567.890.123-45', None, 'Av. Assis Brasil, 2100 - Porto Alegre', '(51) 98123-4567'),
    ('Fernanda', 'Lima', '678.901.234-56', None, 'Rua Mostardeiro, 55 - Porto Alegre', '(51) 99654-3210'),
    ('Rafael', 'Gomes', '789.012.345-67', None, 'Av. Protásio Alves, 900 - Porto Alegre', '(51) 98877-6655'),
    ('Camila', 'Rocha', '890.123.456-78', None, 'Rua Dr. Timóteo, 400 - Porto Alegre', '(51) 99211-0099'),
    ('Gustavo', 'Carvalho', '901.234.567-89', None, 'Av. Carlos Gomes, 1500 - Porto Alegre', '(51) 98300-1234'),
    ('Beatriz', 'Mendes', '012.345.678-90', None, 'Rua Quintino Bocaiúva, 88 - Porto Alegre', '(51) 99988-7766'),
    ('Thiago', 'Barbosa', '111.222.333-44', None, 'Av. Nilo Peçanha, 2700 - Porto Alegre', '(51) 98765-4321'),
    ('Larissa', 'Freitas', '222.333.444-55', None, 'Rua Anita Garibaldi, 1200 - Porto Alegre', '(51) 99345-6789'),
    ('Transportes Gaúcha', 'Ltda', None, '12.345.678/0001-90', 'Av. Sertório, 5000 - Porto Alegre', '(51) 3333-4444'),
    ('Eventos Sul', 'ME', None, '23.456.789/0001-01', 'Rua Voluntários da Pátria, 900 - Porto Alegre', '(51) 3222-1111'),
    ('Construtora Pampa', 'S.A.', None, '34.567.890/0001-12', 'Av. Borges de Medeiros, 2000 - Porto Alegre', '(51) 3011-2233'),
]

VEICULOS = [
    # marca, modelo, placa, categoria, preco_locacao (taxa fixa)
    ('Fiat', 'Mobi', 'ABC1D23', 'E', '50.00'),
    ('Renault', 'Kwid', 'BCD2E34', 'E', '50.00'),
    ('Fiat', 'Argo', 'CDE3F45', 'E', '60.00'),
    ('Chevrolet', 'Onix', 'DEF4G56', 'C', '70.00'),
    ('Hyundai', 'HB20', 'EFG5H67', 'C', '70.00'),
    ('Volkswagen', 'Polo', 'FGH6I78', 'C', '80.00'),
    ('Toyota', 'Corolla', 'GHI7J89', 'M', '100.00'),
    ('Honda', 'Civic', 'HIJ8K90', 'M', '100.00'),
    ('Volkswagen', 'Virtus', 'IJK9L01', 'M', '90.00'),
    ('Jeep', 'Compass', 'JKL0M12', 'S', '150.00'),
    ('Hyundai', 'Creta', 'KLM1N23', 'S', '130.00'),
    ('Toyota', 'SW4', 'LMN2O34', 'S', '180.00'),
    ('BMW', '320i', 'MNO3P45', 'L', '300.00'),
    ('Mercedes-Benz', 'C200', 'NOP4Q56', 'L', '300.00'),
    ('Audi', 'A4', 'OPQ5R67', 'L', '280.00'),
]

MOTIVOS_PREVENTIVA = [
    'Troca de óleo e filtros', 'Revisão dos 20.000 km', 'Alinhamento e balanceamento',
    'Revisão dos 40.000 km', 'Troca de pastilhas de freio',
]
MOTIVOS_CORRETIVA = [
    'Troca de pneu furado', 'Reparo no para-choque', 'Falha no ar-condicionado',
    'Substituição da bateria', 'Barulho na suspensão dianteira',
]
DANOS = [
    'Risco na porta traseira esquerda', 'Retrovisor direito quebrado',
    'Amassado no para-lama', 'Banco traseiro manchado',
]

# Janela do histórico gerado
INICIO_HISTORICO = date(2026, 7, 1)


def aware(dia, hora=9):
    return timezone.make_aware(datetime.combine(dia, time(hora, 0)))


class Command(BaseCommand):
    help = 'Popula o banco com funcionários, clientes, veículos, tarifas, reservas e manutenções de teste.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpar', action='store_true',
            help='Apaga clientes, veículos, reservas, manutenções, tarifas e os usuários de teste antes de popular.',
        )
        parser.add_argument('--seed', type=int, default=42, help='Semente do gerador aleatório.')

    def handle(self, *args, **opts):
        self.rng = random.Random(opts['seed'])
        self.hoje = timezone.localdate()

        if opts['limpar']:
            self.limpar()
        elif Cliente.objects.exists() or Veiculo.objects.exists():
            raise CommandError('O banco já tem clientes/veículos. Use --limpar para recriar os dados de teste.')

        with transaction.atomic():
            self.criar_tarifas()
            self.criar_funcionarios()
            clientes = [self.criar_cliente(*c) for c in CLIENTES]
            veiculos = [
                Veiculo.objects.create(marca=m, modelo=mo, placa=p, categoria=c, preco_locacao=Decimal(v))
                for m, mo, p, c, v in VEICULOS
            ]
            usuarios = list(User.objects.filter(is_active=True))
            for i, veiculo in enumerate(veiculos):
                self.gerar_historico(veiculo, i, clientes, usuarios)

        self.resumo()

    # ------------------------------------------------------------------ setup

    def limpar(self):
        with transaction.atomic():
            Reserva.objects.all().delete()
            Manutencao.objects.all().delete()
            Veiculo.objects.all().delete()
            Cliente.objects.all().delete()
            Tarifa.objects.all().delete()
            usernames = [f[0] for f in FUNCIONARIOS]
            Funcionario.objects.filter(user__username__in=usernames).delete()
            User.objects.filter(username__in=usernames).delete()
        self.stdout.write(self.style.WARNING('Dados de teste anteriores removidos.'))

    def criar_tarifas(self):
        for categoria, valor in TARIFAS.items():
            Tarifa.objects.update_or_create(categoria=categoria, defaults={'valor_diaria': Decimal(valor)})

    def criar_funcionarios(self):
        for username, nome, sobrenome, cargo, sexo, admin, ativo in FUNCIONARIOS:
            user = User.objects.create_user(
                username=username, password=SENHA, first_name=nome, last_name=sobrenome,
                is_superuser=admin, is_staff=admin, is_active=ativo,
            )
            Funcionario.objects.create(
                user=user, nome=nome, sobrenome=sobrenome, cargo=cargo,
                sexo=sexo, isAdmin=admin, ativo=ativo,
            )

    def criar_cliente(self, nome, sobrenome, cpf, cnpj, endereco, telefone):
        cliente = Cliente.objects.create(
            nome=nome, sobrenome=sobrenome, cpf=cpf, cnpj=cnpj, endereco=endereco, telefone=telefone,
        )
        dias_atras = self.rng.randint(120, 400)
        Cliente.objects.filter(pk=cliente.pk).update(data_cadastro=aware(self.hoje - timedelta(days=dias_atras)))
        return cliente

    # --------------------------------------------------------------- histórico

    def gerar_historico(self, veiculo, indice, clientes, usuarios):
        """Gera uma linha do tempo sem sobreposição para o veículo e termina
        num estado atual coerente com o status do veículo."""
        # Estado atual: distribui entre os veículos
        estado_final = ['andamento', 'pendente', 'manutencao', 'livre', 'livre'][indice % 5]
        km = Decimal(self.rng.randint(5000, 60000))
        dia = INICIO_HISTORICO + timedelta(days=self.rng.randint(0, 10))
        limite = self.hoje - timedelta(days=12)

        while dia < limite:
            sorteio = self.rng.random()
            if sorteio < 0.12:
                dia, km = self.manutencao_concluida(veiculo, dia, km)
            elif sorteio < 0.22:
                dia = self.reserva_cancelada(veiculo, dia, clientes, usuarios)
            else:
                dia, km = self.reserva_concluida(veiculo, dia, km, clientes, usuarios)
            dia += timedelta(days=self.rng.randint(1, 6))

        if estado_final == 'andamento':
            inicio = self.hoje - timedelta(days=self.rng.randint(1, 4))
            reserva = self.nova_reserva(veiculo, inicio, inicio + timedelta(days=self.rng.randint(5, 10)), clientes, usuarios)
            self.retirar(reserva, km, inicio)
        elif estado_final == 'pendente':
            inicio = self.hoje + timedelta(days=self.rng.randint(1, 12))
            self.nova_reserva(veiculo, inicio, inicio + timedelta(days=self.rng.randint(2, 7)), clientes, usuarios)
        elif estado_final == 'manutencao':
            self.manutencao_aberta(veiculo)

    def nova_reserva(self, veiculo, inicio, fim, clientes, usuarios):
        veiculo.refresh_from_db()
        reserva = Reserva(
            cliente=self.rng.choice(clientes), veiculo=veiculo, status='P',
            data_inicio=aware(inicio, 9), data_fim=aware(fim, 18),
            user=self.rng.choice(usuarios) if usuarios else None,
        )
        reserva.calcular_valor()
        reserva.save()
        Reserva.objects.filter(pk=reserva.pk).update(
            data_cadastro=aware(inicio - timedelta(days=self.rng.randint(1, 15)), 14))
        Veiculo.objects.filter(pk=veiculo.pk).update(status='R')
        return reserva

    def retirar(self, reserva, km, dia):
        retirada = Retirada.objects.create(
            reserva=reserva, quilometragem_inicial=km,
            nivel_combustivel=Decimal(self.rng.choice([50, 75, 100])),
        )
        Retirada.objects.filter(pk=retirada.pk).update(data_retirada=aware(dia, 10))

    def reserva_concluida(self, veiculo, dia, km, clientes, usuarios):
        duracao = self.rng.randint(1, 10)
        fim = dia + timedelta(days=duracao)
        reserva = self.nova_reserva(veiculo, dia, fim, clientes, usuarios)
        self.retirar(reserva, km, dia)

        atraso = self.rng.choices([0, 1, 2, 3], weights=[75, 13, 8, 4])[0]
        danos = self.rng.random() < 0.12
        km_final = km + Decimal(self.rng.randint(80, 350) * duracao)
        devolucao = Devolucao.objects.create(
            reserva=reserva,
            quilometragem_final=km_final,
            danos=danos,
            descricao_danos=self.rng.choice(DANOS) if danos else '',
            multa_atraso=reserva.valor_diaria * atraso * Decimal('1.5'),
            multa_danos=Decimal(self.rng.choice([250, 400, 800, 1200])) if danos else Decimal('0'),
        )
        entregue = fim + timedelta(days=atraso)
        Devolucao.objects.filter(pk=devolucao.pk).update(data_devolucao=aware(entregue, 17))
        return entregue, km_final

    def reserva_cancelada(self, veiculo, dia, clientes, usuarios):
        reserva = self.nova_reserva(veiculo, dia, dia + timedelta(days=self.rng.randint(1, 6)), clientes, usuarios)
        Reserva.objects.filter(pk=reserva.pk).update(status='X')
        Veiculo.objects.filter(pk=veiculo.pk).update(status='D')
        # cancelada: o carro fica livre, segue a linha do tempo do mesmo dia
        return dia

    def manutencao_concluida(self, veiculo, dia, km):
        preventiva = self.rng.random() < 0.6
        duracao = self.rng.randint(1, 5)
        manutencao = Manutencao.objects.create(
            veiculo=veiculo,
            tipo='P' if preventiva else 'C',
            motivo=self.rng.choice(MOTIVOS_PREVENTIVA if preventiva else MOTIVOS_CORRETIVA),
            previsao_conclusao=dia + timedelta(days=duracao),
            custo=Decimal(self.rng.randint(150, 900 if preventiva else 2500)),
        )
        conclusao = dia + timedelta(days=duracao + self.rng.choice([0, 0, 0, 1, 2]))
        Manutencao.objects.filter(pk=manutencao.pk).update(
            data_inicio=aware(dia, 8), data_conclusao=aware(conclusao, 16))
        return conclusao, km

    def manutencao_aberta(self, veiculo):
        inicio = self.hoje - timedelta(days=self.rng.randint(1, 5))
        preventiva = self.rng.random() < 0.5
        manutencao = Manutencao.objects.create(
            veiculo=veiculo,
            tipo='P' if preventiva else 'C',
            motivo=self.rng.choice(MOTIVOS_PREVENTIVA if preventiva else MOTIVOS_CORRETIVA),
            previsao_conclusao=self.hoje + timedelta(days=self.rng.randint(-1, 6)),
            custo=None,
        )
        Manutencao.objects.filter(pk=manutencao.pk).update(data_inicio=aware(inicio, 8))
        Veiculo.objects.filter(pk=veiculo.pk).update(status='M')

    # ------------------------------------------------------------------ saída

    def resumo(self):
        self.stdout.write(self.style.SUCCESS('Banco populado:'))
        for modelo in (Tarifa, Funcionario, Cliente, Veiculo, Reserva, Retirada, Devolucao, Manutencao):
            self.stdout.write(f'  {modelo._meta.verbose_name_plural}: {modelo.objects.count()}')
        por_status = {s: Reserva.objects.filter(status=s).count() for s in 'PACX'}
        self.stdout.write(f'  reservas por status (P/A/C/X): {por_status}')
        self.stdout.write(f'Usuários de teste: {", ".join(f[0] for f in FUNCIONARIOS)} (senha: {SENHA})')
