from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    CATEGORIA_CHOICES,
    Cliente,
    Devolucao,
    Funcionario,
    Manutencao,
    Reserva,
    Retirada,
    Tarifa,
    Veiculo,
)

User = get_user_model()


class LocacaoTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='administrador',
            password='Senha-Forte-2026!',
            is_superuser=True,
        )
        self.funcionario_user = User.objects.create_user(
            username='funcionario',
            password='Senha-Forte-2026!',
        )

    def autenticar_admin(self):
        self.client.force_login(self.admin)

    def criar_veiculo(self, **overrides):
        dados = {
            'modelo': 'Onix',
            'placa': 'ABC1234',
            'categoria': 'E',
            'status': 'D',
            'preco_locacao': '100.00',
            'marca': 'Chevrolet',
        }
        dados.update(overrides)
        return Veiculo.objects.create(**dados)

    def criar_cliente(self, **overrides):
        dados = {
            'nome': 'Ana',
            'sobrenome': 'Silva',
            'cpf': '123.456.789-00',
            'endereco': 'Rua A, 10',
            'telefone': '11999999999',
        }
        dados.update(overrides)
        return Cliente.objects.create(**dados)

    def post_funcionario(self, **overrides):
        dados = {
            'nome': 'Joana',
            'sobrenome': 'Souza',
            'cargo': 'Atendente',
            'sexo': 'F',
            'username': 'joana',
            'password1': 'Senha-Forte-Para-Conta-2026!',
            'password2': 'Senha-Forte-Para-Conta-2026!',
        }
        dados.update(overrides)
        return dados

    def data_locacao(self, dias_a_frente):
        data = timezone.localdate() + timedelta(days=dias_a_frente)
        return datetime.combine(data, time(10, 0)).strftime('%Y-%m-%d %H:%M:%S')


class AutenticacaoEPermissoesTests(LocacaoTestCase):
    def test_login_e_logout(self):
        resposta = self.client.post(
            reverse('login'),
            {'username': self.funcionario_user.username, 'password': 'Senha-Forte-2026!'},
        )

        self.assertRedirects(resposta, reverse('home'))
        self.assertTrue('_auth_user_id' in self.client.session)

        resposta = self.client.post(reverse('logout'))

        self.assertRedirects(resposta, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_rotas_protegidas_redirecionam_usuario_anonimo(self):
        urls_protegidas = (
            reverse('home'),
            reverse('listar_clientes'),
            reverse('cadastrar_cliente'),
            reverse('reservar_veiculo'),
            reverse('listar_reservas'),
            reverse('listar_veiculos_disponiveis'),
            reverse('registrar_retirada'),
            reverse('registrar_devolucao'),
        )

        for url in urls_protegidas:
            with self.subTest(url=url):
                resposta = self.client.get(url)
                self.assertRedirects(
                    resposta,
                    f'{reverse("login")}?next={url}',
                    fetch_redirect_response=False,
                )

    def test_rotas_administrativas_negam_acesso_a_funcionario(self):
        self.client.force_login(self.funcionario_user)
        self.client.raise_request_exception = False

        for nome_rota in (
            'listar_funcionarios',
            'cadastrar_funcionario',
            'listar_veiculos',
            'cadastrar_veiculo',
            'listar_manutencoes',
            'registrar_manutencao',
            'configurar_tarifas',
        ):
            with self.subTest(nome_rota=nome_rota):
                resposta = self.client.get(reverse(nome_rota))
                self.assertEqual(resposta.status_code, 403)

    def test_usuario_admin_acessa_rota_administrativa(self):
        self.autenticar_admin()

        resposta = self.client.get(reverse('listar_veiculos'))

        self.assertEqual(resposta.status_code, 200)


class ClientesTests(LocacaoTestCase):
    def test_crud_cliente_e_validacao_de_documento(self):
        self.client.force_login(self.funcionario_user)

        resposta = self.client.post(reverse('cadastrar_cliente'), {
            'nome': 'Maria',
            'sobrenome': 'Oliveira',
            'endereco': 'Rua B, 20',
            'telefone': '11988887777',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Cliente.objects.count(), 0)

        resposta = self.client.post(reverse('cadastrar_cliente'), {
            'nome': 'Maria',
            'sobrenome': 'Oliveira',
            'cpf': '987.654.321-00',
            'endereco': 'Rua B, 20',
            'telefone': '11988887777',
        })
        self.assertRedirects(resposta, reverse('listar_clientes'))
        cliente = Cliente.objects.get(cpf='987.654.321-00')
        self.assertEqual(cliente.nome, 'Maria')

        resposta = self.client.post(
            reverse('editar_cliente', args=[cliente.pk]),
            {
                'nome': 'Mariana',
                'sobrenome': 'Oliveira',
                'cpf': cliente.cpf,
                'endereco': 'Rua C, 30',
                'telefone': '11977776666',
            },
        )
        self.assertRedirects(resposta, reverse('listar_clientes'))
        cliente.refresh_from_db()
        self.assertEqual(cliente.nome, 'Mariana')
        self.assertEqual(cliente.endereco, 'Rua C, 30')

        resposta = self.client.get(reverse('excluir_cliente', args=[cliente.pk]))
        self.assertRedirects(resposta, reverse('listar_clientes'))
        self.assertFalse(Cliente.objects.filter(pk=cliente.pk).exists())

    def test_cliente_pode_ser_cadastrado_com_cnpj(self):
        self.client.force_login(self.funcionario_user)

        resposta = self.client.post(reverse('cadastrar_cliente'), {
            'nome': 'Empresa',
            'sobrenome': 'Exemplo',
            'cnpj': '12.345.678/0001-90',
            'endereco': 'Rua D, 40',
            'telefone': '1133334444',
        })

        self.assertRedirects(resposta, reverse('listar_clientes'))
        self.assertTrue(Cliente.objects.filter(cnpj='12.345.678/0001-90').exists())


class FuncionariosTests(LocacaoTestCase):
    def test_funcionario_marcado_como_admin_recebe_permissoes(self):
        self.autenticar_admin()

        resposta = self.client.post(
            reverse('cadastrar_funcionario'),
            self.post_funcionario(username='gerente', isAdmin='on'),
        )

        self.assertRedirects(resposta, reverse('listar_funcionarios'))
        funcionario = Funcionario.objects.get(user__username='gerente')
        self.assertTrue(funcionario.isAdmin)
        self.assertTrue(funcionario.user.is_superuser)

        self.client.force_login(funcionario.user)
        self.assertEqual(
            self.client.get(reverse('listar_veiculos')).status_code,
            200,
        )

    def test_crud_funcionario_e_sincronizacao_da_conta(self):
        self.autenticar_admin()
        url_cadastro = reverse('cadastrar_funcionario')

        resposta = self.client.post(
            url_cadastro,
            self.post_funcionario(password2='Senha-diferente-2026!'),
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Funcionario.objects.count(), 0)

        resposta = self.client.post(url_cadastro, self.post_funcionario())
        self.assertRedirects(resposta, reverse('listar_funcionarios'))
        funcionario = Funcionario.objects.get(user__username='joana')
        self.assertFalse(funcionario.user.is_superuser)

        resposta = self.client.post(
            reverse('editar_funcionario', args=[funcionario.pk]),
            self.post_funcionario(
                nome='Joana Atualizada',
                username='joana',
                password1='',
                password2='',
            ),
        )
        self.assertRedirects(resposta, reverse('listar_funcionarios'))
        funcionario.refresh_from_db()
        self.assertEqual(funcionario.nome, 'Joana Atualizada')

        resposta = self.client.get(
            reverse('desativar_funcionario', args=[funcionario.pk]))
        self.assertRedirects(resposta, reverse('listar_funcionarios'))
        funcionario.refresh_from_db()
        funcionario.user.refresh_from_db()
        self.assertFalse(funcionario.ativo)
        self.assertFalse(funcionario.user.is_active)

        resposta = self.client.get(
            reverse('ativar_funcionario', args=[funcionario.pk]))
        self.assertRedirects(resposta, reverse('funcionarios_inativos'))
        funcionario.refresh_from_db()
        funcionario.user.refresh_from_db()
        self.assertTrue(funcionario.ativo)
        self.assertTrue(funcionario.user.is_active)

        resposta = self.client.get(
            reverse('excluir_funcionario', args=[funcionario.pk]))
        self.assertRedirects(resposta, reverse('listar_funcionarios'))
        self.assertFalse(Funcionario.objects.filter(pk=funcionario.pk).exists())
        self.assertFalse(User.objects.filter(username='joana').exists())


class VeiculosTests(LocacaoTestCase):
    def test_crud_veiculo_e_filtro_por_categoria_e_status(self):
        self.autenticar_admin()
        url_cadastro = reverse('cadastrar_veiculo')
        dados = {
            'modelo': 'Creta',
            'placa': 'DEF5678',
            'categoria': 'S',
            'status': 'D',
            'preco_locacao': '150.00',
            'marca': 'Hyundai',
        }

        resposta = self.client.post(url_cadastro, dados)
        self.assertRedirects(resposta, reverse('listar_veiculos'))
        veiculo = Veiculo.objects.get(placa='DEF5678')
        self.assertEqual(veiculo.categoria, 'S')
        self.assertEqual(veiculo.status, 'D')

        resposta = self.client.post(url_cadastro, {
            **dados,
            'modelo': 'Outro',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Veiculo.objects.count(), 1)

        resposta = self.client.post(
            reverse('editar_veiculo', args=[veiculo.pk]),
            {**dados, 'modelo': 'Creta Atualizado', 'status': 'M'},
        )
        self.assertRedirects(resposta, reverse('listar_veiculos'))
        veiculo.refresh_from_db()
        self.assertEqual(veiculo.modelo, 'Creta Atualizado')
        self.assertEqual(veiculo.status, 'M')

        self.criar_veiculo(
            modelo='Civic',
            placa='GHI9012',
            categoria='M',
        )
        resposta = self.client.get(
            reverse('listar_veiculos'),
            {'categoria_pesquisa': 'S', 'status_pesquisa': 'M'},
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(
            list(resposta.context['veiculos']),
            [veiculo],
        )

        veiculo.status = 'D'
        veiculo.save(update_fields=['status'])
        resposta = self.client.get(reverse('excluir_veiculo', args=[veiculo.pk]))
        self.assertRedirects(resposta, reverse('listar_veiculos'))
        self.assertFalse(Veiculo.objects.filter(pk=veiculo.pk).exists())

    def test_categoria_status_invalidos_sao_rejeitados_pelo_formulario(self):
        from .forms import VeiculoForm

        form = VeiculoForm({
            'modelo': 'Modelo',
            'placa': 'JKL3456',
            'categoria': 'Z',
            'status': 'Z',
            'preco_locacao': '100.00',
            'marca': 'Marca',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('categoria', form.errors)
        self.assertIn('status', form.errors)


class ManutencoesETarifasTests(LocacaoTestCase):
    def test_registra_e_conclui_manutencao_atualizando_custo_e_status(self):
        self.autenticar_admin()
        veiculo = self.criar_veiculo(placa='MNT1234')
        previsao = (timezone.localdate() + timedelta(days=5)).isoformat()

        resposta = self.client.post(reverse('registrar_manutencao'), {
            'veiculo': veiculo.pk,
            'tipo': 'P',
            'motivo': 'Revisão preventiva',
            'previsao_conclusao': previsao,
        })
        self.assertRedirects(resposta, reverse('listar_manutencoes'))
        manutencao = Manutencao.objects.get(veiculo=veiculo)
        veiculo.refresh_from_db()
        self.assertEqual(veiculo.status, 'M')
        self.assertIsNone(manutencao.data_conclusao)
        self.assertIsNone(manutencao.custo)

        resposta = self.client.post(
            reverse('concluir_manutencao', args=[manutencao.pk]),
            {'custo': '275.50'},
        )
        self.assertRedirects(resposta, reverse('listar_manutencoes'))
        manutencao.refresh_from_db()
        veiculo.refresh_from_db()
        self.assertEqual(manutencao.custo, Decimal('275.50'))
        self.assertIsNotNone(manutencao.data_conclusao)
        self.assertEqual(veiculo.status, 'D')

    def test_cancelar_manutencao_marca_veiculo_com_problema(self):
        self.autenticar_admin()
        veiculo = self.criar_veiculo(placa='MNT5678', status='M')
        manutencao = Manutencao.objects.create(
            veiculo=veiculo,
            tipo='C',
            motivo='Falha no motor',
            previsao_conclusao=timezone.localdate() + timedelta(days=2),
        )

        resposta = self.client.post(
            reverse('cancelar_manutencao', args=[manutencao.pk]))

        self.assertRedirects(resposta, reverse('listar_manutencoes'))
        manutencao.refresh_from_db()
        veiculo.refresh_from_db()
        self.assertIsNotNone(manutencao.data_conclusao)
        self.assertIsNone(manutencao.custo)
        self.assertEqual(veiculo.status, 'P')

    def test_configura_tarifas_por_categoria(self):
        self.autenticar_admin()
        dados = {
            f'categoria_{codigo}': f'{index * 10}.00'
            for index, (codigo, _) in enumerate(CATEGORIA_CHOICES, start=1)
        }

        resposta = self.client.post(reverse('configurar_tarifas'), dados)

        self.assertRedirects(resposta, reverse('configurar_tarifas'))
        self.assertEqual(Tarifa.objects.count(), len(CATEGORIA_CHOICES))
        for index, (codigo, _) in enumerate(CATEGORIA_CHOICES, start=1):
            with self.subTest(categoria=codigo):
                tarifa = Tarifa.objects.get(categoria=codigo)
                self.assertEqual(tarifa.valor_diaria, Decimal(f'{index * 10}.00'))


class FluxoLocacaoTests(LocacaoTestCase):
    def test_reserva_retirada_e_devolucao_calculam_valores_e_status(self):
        self.client.force_login(self.funcionario_user)
        cliente = self.criar_cliente()
        veiculo = self.criar_veiculo()
        Tarifa.objects.create(categoria='E', valor_diaria=Decimal('50.00'))

        resposta = self.client.post(reverse('reservar_veiculo'), {
            'cliente': cliente.pk,
            'veiculo': veiculo.pk,
            'data_inicio': self.data_locacao(30),
            'data_fim': self.data_locacao(32),
        })

        self.assertRedirects(resposta, reverse('listar_reservas'))
        reserva = Reserva.objects.get(cliente=cliente, veiculo=veiculo)
        veiculo.refresh_from_db()
        self.assertEqual(reserva.status, 'P')
        self.assertEqual(reserva.quantidade_dias, 2)
        self.assertEqual(reserva.valor_locacao, Decimal('100.00'))
        self.assertEqual(reserva.valor_diaria, Decimal('50.00'))
        self.assertEqual(reserva.valor_total, Decimal('200.00'))
        self.assertEqual(veiculo.status, 'R')

        resposta = self.client.post(
            reverse('confirmar_retirada', args=[reserva.pk]),
            {
                'quilometragem_inicial': '10000',
                'nivel_combustivel': '45.5',
            },
        )
        self.assertRedirects(resposta, reverse('listar_reservas'))
        reserva.refresh_from_db()
        veiculo.refresh_from_db()
        retirada = Retirada.objects.get(reserva=reserva)
        self.assertEqual(reserva.status, 'A')
        self.assertEqual(veiculo.status, 'I')
        self.assertEqual(retirada.quilometragem_inicial, Decimal('10000'))

        resposta = self.client.post(
            reverse('confirmar_devolucao', args=[reserva.pk]),
            {
                'quilometragem_final': '10125',
                'danos': 'on',
                'descricao_danos': 'Risco na porta',
                'multa_danos': '25.00',
            },
        )
        self.assertRedirects(resposta, reverse('listar_reservas'))
        reserva.refresh_from_db()
        veiculo.refresh_from_db()
        devolucao = Devolucao.objects.get(reserva=reserva)
        self.assertEqual(reserva.status, 'C')
        self.assertEqual(veiculo.status, 'D')
        self.assertEqual(devolucao.multa_atraso, Decimal('0'))
        self.assertEqual(devolucao.multa_danos, Decimal('25.00'))
        self.assertEqual(devolucao.valor_multa_total, Decimal('25.00'))
        self.assertEqual(devolucao.valor_final, Decimal('225.00'))

    def test_reserva_invalida_nao_altera_status_do_veiculo(self):
        cliente = self.criar_cliente()
        veiculo = self.criar_veiculo()
        self.client.force_login(self.funcionario_user)

        resposta = self.client.post(reverse('reservar_veiculo'), {
            'cliente': cliente.pk,
            'veiculo': veiculo.pk,
            'data_inicio': self.data_locacao(30),
            'data_fim': self.data_locacao(30),
        })

        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Reserva.objects.exists())
        self.assertIn(
            'A data de retirada deve ser anterior à data de devolução.',
            resposta.context['formulario'].errors['__all__'],
        )
        veiculo.refresh_from_db()
        self.assertEqual(veiculo.status, 'D')

        resposta = self.client.post(reverse('reservar_veiculo'), {
            'cliente': cliente.pk,
            'veiculo': veiculo.pk,
            'data_inicio': self.data_locacao(30),
            'data_fim': self.data_locacao(32),
        })

        self.assertEqual(resposta.status_code, 200)
        self.assertIn(
            'veiculo',
            resposta.context['formulario'].errors,
        )
        self.assertFalse(Reserva.objects.exists())
