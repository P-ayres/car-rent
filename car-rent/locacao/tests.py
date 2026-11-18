from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Cliente, Devolucao, Manutencao, Reserva, Veiculo


def data(ano, mes, dia, hora=10):
    return timezone.make_aware(datetime(ano, mes, dia, hora))


class RelatorioOperacionalTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='operador', password='senha-teste')
        self.client.force_login(self.user)

        self.cliente = Cliente.objects.create(
            nome='ana', sobrenome='silva', cpf='111.111.111-11')
        self.veiculo = Veiculo.objects.create(
            modelo='Onix', placa='ABC1D23', categoria='C',
            preco_locacao=Decimal('50'), marca='Chevrolet')

        self.reserva_no_periodo = self._reserva(
            data(2026, 11, 5), data(2026, 11, 8), Decimal('350'), 'C')
        # bulk_create evita o fluxo de Devolucao.save(), que exige retirada.
        Devolucao.objects.bulk_create([Devolucao(
            reserva=self.reserva_no_periodo, quilometragem_final=100,
            multa_atraso=Decimal('20'), multa_danos=Decimal('30'),
        )])
        self.reserva_cancelada = self._reserva(
            data(2026, 11, 10), data(2026, 11, 12), Decimal('999'), 'X')
        self.reserva_fora = self._reserva(
            data(2026, 12, 10), data(2026, 12, 12), Decimal('500'), 'P')

        self.manutencao_concluida = self._manutencao(
            data(2026, 11, 2), data(2026, 11, 4), Decimal('120'))
        self.manutencao_fora = self._manutencao(
            data(2026, 9, 1), data(2026, 9, 3), Decimal('800'))

    def _reserva(self, inicio, fim, total, status):
        return Reserva.objects.create(
            cliente=self.cliente, veiculo=self.veiculo, status=status,
            data_inicio=inicio, data_fim=fim, valor_total=total)

    def _manutencao(self, inicio, conclusao, custo):
        manutencao = Manutencao.objects.create(
            veiculo=self.veiculo, tipo='P', motivo='Revisão',
            previsao_conclusao=conclusao.date(), custo=custo,
            data_conclusao=conclusao)
        Manutencao.objects.filter(pk=manutencao.pk).update(data_inicio=inicio)
        return manutencao

    def gerar(self, **params):
        return self.client.get(reverse('relatorios'), params)

    def test_exige_login(self):
        self.client.logout()
        resposta = self.client.get(reverse('relatorios'))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse('login'), resposta['Location'])

    def test_tela_sem_periodo_exibe_apenas_filtro(self):
        resposta = self.gerar()
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Gerar Relatório')
        self.assertNotIn('relatorio', resposta.context)

    def test_relatorio_filtra_por_periodo_e_calcula_valores(self):
        resposta = self.gerar(data_inicio='2026-11-01', data_fim='2026-11-30')
        relatorio = resposta.context['relatorio']

        self.assertEqual(
            set(relatorio['reservas']),
            {self.reserva_no_periodo, self.reserva_cancelada})
        self.assertEqual(
            list(relatorio['manutencoes']), [self.manutencao_concluida])

        self.assertEqual(relatorio['receita_locacoes'], Decimal('350'))
        self.assertEqual(relatorio['receita_multas'], Decimal('50'))
        self.assertEqual(relatorio['receita_total'], Decimal('400'))
        self.assertEqual(relatorio['custo_manutencoes'], Decimal('120'))
        self.assertEqual(relatorio['valor_agregado'], Decimal('280'))

    def test_reserva_que_cruza_o_periodo_entra_no_relatorio(self):
        resposta = self.gerar(data_inicio='2026-11-07', data_fim='2026-11-07')
        self.assertIn(
            self.reserva_no_periodo, resposta.context['relatorio']['reservas'])

    def test_manutencao_em_andamento_entra_no_relatorio(self):
        em_andamento = Manutencao.objects.create(
            veiculo=self.veiculo, tipo='C', motivo='Freio',
            previsao_conclusao=data(2026, 11, 30).date())
        Manutencao.objects.filter(pk=em_andamento.pk).update(
            data_inicio=data(2026, 10, 20))

        resposta = self.gerar(data_inicio='2026-11-01', data_fim='2026-11-30')
        self.assertIn(
            em_andamento, resposta.context['relatorio']['manutencoes'])

    def test_periodo_invalido_exibe_erro(self):
        resposta = self.gerar(data_inicio='2026-11-30', data_fim='2026-11-01')
        self.assertNotIn('relatorio', resposta.context)
        self.assertContains(
            resposta, 'A data final não pode ser anterior à data inicial.')

    def test_controles_nao_sao_impressos(self):
        resposta = self.gerar(data_inicio='2026-11-01', data_fim='2026-11-30')
        self.assertContains(resposta, 'class="filtro-relatorio card nao-imprimir"')
        self.assertContains(resposta, 'class="button nao-imprimir"')
        self.assertContains(resposta, 'R$ 280,00')
