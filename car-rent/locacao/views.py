from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone
from django.views.decorators.http import require_POST
from functools import wraps
from .forms import (
    ClienteForm,
    ConfirmarDevolucaoForm,
    ConfirmarRetiradaForm,
    FuncionarioForm,
    ManutencaoForm,
    TarifaForm,
    ReservaForm, VeiculoForm,
)
from .models import (
    CATEGORIA_CHOICES,
    STATUS_CHOICES,
    Cliente,
    Devolucao,
    Funcionario,
    Manutencao,
    Reserva,
    Retirada,
    Veiculo,
)

# Create your views here.

User = get_user_model()


def formatar_valor(valor):
    """Formata um Decimal como moeda brasileira: 1234.5 -> 'R$ 1.234,50'."""
    texto = f'{valor:,.2f}'.replace(
        ',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {texto}'


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapped_view


def salvar_funcionario_com_usuario(form):
    funcionario = form.save(commit=False)
    password = form.cleaned_data.get('password1')

    if funcionario.user_id:
        usuario = funcionario.user
        usuario.username = form.cleaned_data['username']
        usuario.is_superuser = funcionario.isAdmin
        usuario.is_active = funcionario.ativo
        if password:
            usuario.set_password(password)
        usuario.save()
    else:
        usuario = User.objects.create_user(
            username=form.cleaned_data['username'],
            password=password,
            is_superuser=funcionario.isAdmin,
            is_active=funcionario.ativo,
        )
        funcionario.user = usuario

    funcionario.save()
    return funcionario


@admin_required
def cadastrar_funcionario(request):
    form = FuncionarioForm()

    if request.method == 'POST':
        form = FuncionarioForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                funcionario = salvar_funcionario_com_usuario(form)

            messages.success(
                request,
                f'Funcionário {funcionario.nome} cadastrado com sucesso!',
            )

            return redirect('listar_funcionarios')

    dados = {
        'formulario': form
    }

    return render(request, "cadastrar_funcionario.html", dados)


@admin_required
def listar_funcionarios(request):

    ordem = request.GET.get('ordem')
    nome_da_pesquisa = request.GET.get('nome_da_pesquisa', '')

    funcionarios = Funcionario.objects.filter(
        nome__icontains=nome_da_pesquisa,
        ativo=True
    ).order_by(Lower('nome'))

    if ordem == 'decrescente':
        funcionarios = Funcionario.objects.filter(
            nome__icontains=nome_da_pesquisa,
            ativo=True
        ).order_by(Lower('nome').desc())

    dados = {
        'funcionarios': funcionarios,
        'nome_da_pesquisa': nome_da_pesquisa,
    }

    return render(request, 'listar_funcionarios.html', dados)


@admin_required
def editar_funcionario(request, id):

    funcionario = Funcionario.objects.select_related('user').get(id=id)

    form = FuncionarioForm(instance=funcionario)

    if request.method == 'POST':
        form = FuncionarioForm(request.POST, instance=funcionario)

        if form.is_valid():
            with transaction.atomic():
                funcionario = salvar_funcionario_com_usuario(form)

            messages.success(
                request,
                f'Funcionário {funcionario.nome} alterado com sucesso!',
            )

            return redirect('listar_funcionarios')

    dados = {
        'formulario': form
    }

    return render(request, 'editar_funcionario.html', dados)


@admin_required
def excluir_funcionario(request, id):

    funcionario = Funcionario.objects.select_related('user').get(id=id)

    nome = funcionario.nome
    sobrenome = funcionario.sobrenome

    with transaction.atomic():
        if funcionario.user_id:
            funcionario.user.delete()
        funcionario.delete()

    mensagem = f'Funcionário {nome} {sobrenome} Excluído com sucesso'
    messages.success(request, mensagem)

    return redirect('listar_funcionarios')


@admin_required
def funcionarios_inativos(request):

    funcionarios = Funcionario.objects.filter(
        ativo=False
    )

    dados = {
        'funcionarios': funcionarios
    }

    return render(request, 'funcionarios_inativos.html', dados)


@admin_required
def ativar_funcionario(request, id):

    funcionario = Funcionario.objects.get(id=id)

    nome = funcionario.nome
    sobrenome = funcionario.sobrenome

    funcionario.ativo = True

    with transaction.atomic():
        funcionario.save()

        if funcionario.user_id:
            funcionario.user.is_active = True
            funcionario.user.save(update_fields=['is_active'])

    mensagem = f'Funcionario {nome} {sobrenome} Ativado com Sucesso'
    messages.success(request, mensagem)

    return redirect('funcionarios_inativos')


@admin_required
def desativar_funcionario(request, id):

    funcionario = Funcionario.objects.get(id=id)

    nome = funcionario.nome
    sobrenome = funcionario.sobrenome

    funcionario.ativo = False

    with transaction.atomic():
        funcionario.save()

        if funcionario.user_id:
            funcionario.user.is_active = False
            funcionario.user.save(update_fields=['is_active'])

    mensagem = f'Funcionário {nome} {sobrenome} Desativado com sucesso'
    messages.success(request, mensagem)

    return redirect('listar_funcionarios')


@admin_required
def cadastrar_veiculo(request):

    if request.method == 'POST':
        form = VeiculoForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                veiculo = form.save()

            messages.success(
                request,
                f'Veículo {veiculo.modelo} cadastrado com sucesso!',
            )

            return redirect('listar_veiculos')

    else:
        form = VeiculoForm()

    dados = {
        'formulario': form
    }

    return render(request, 'cadastrar_veiculo.html', dados)


@admin_required
def listar_veiculos(request):
    ordem = request.GET.get('ordem')
    nome_da_pesquisa = request.GET.get('nome_da_pesquisa', '')
    categoria_pesquisa = request.GET.get('categoria_pesquisa', '')
    status_pesquisa = request.GET.get('status_pesquisa', '')

    veiculos = Veiculo.objects.filter(
        modelo__icontains=nome_da_pesquisa,
        categoria__icontains=categoria_pesquisa,
        status__icontains=status_pesquisa,
    ).order_by(Lower('modelo'))

    if ordem == 'decrescente':
        veiculos = Veiculo.objects.filter(
            modelo__icontains=nome_da_pesquisa,
            categoria__icontains=categoria_pesquisa,
            status__icontains=status_pesquisa,
        ).order_by(Lower('modelo').desc())

    dados = {
        'veiculos': veiculos,
        'nome_da_pesquisa': nome_da_pesquisa,
        'categoria_pesquisa': categoria_pesquisa,
        'status_pesquisa': status_pesquisa,
        'categorias': CATEGORIA_CHOICES,
        'status_opcoes': STATUS_CHOICES,
        'ordem': ordem,
        'parametros_filtro': request.GET.urlencode(),
    }

    return render(request, 'listar_veiculos.html', dados)


@admin_required
def editar_veiculo(request, id):

    veiculo = Veiculo.objects.get(id=id)

    if request.method == 'POST':
        form = VeiculoForm(request.POST, instance=veiculo)

        if form.is_valid():
            with transaction.atomic():
                veiculo = form.save()

            messages.success(
                request,
                f'Veículo {veiculo.modelo} atualizado com sucesso!',
            )

            return redirect('listar_veiculos')

    else:
        form = VeiculoForm(instance=veiculo)

    dados = {
        'formulario': form
    }

    return render(request, 'cadastrar_veiculo.html', dados)


@admin_required
def excluir_veiculo(request, id):

    with transaction.atomic():
        veiculo = Veiculo.objects.select_for_update().get(id=id)

        if veiculo.status != 'D':
            messages.error(
                request, 'Somente veículos disponíveis podem ser removidos.')
            return redirect('listar_veiculos')

        modelo = veiculo.modelo
        veiculo.delete()

    mensagem = f'Veículo {modelo} Excluído com sucesso'
    messages.success(request, mensagem)

    return redirect('listar_veiculos')


@login_required
def cadastrar_cliente(request):
    form = ClienteForm()

    if request.method == 'POST':
        form = ClienteForm(request.POST)

        if form.is_valid():
            cliente = form.save()

            messages.success(
                request,
                f'Cliente {cliente.nome} cadastrado com sucesso!',
            )

            return redirect('listar_clientes')

    dados = {
        'formulario': form
    }

    return render(request, 'cadastrar_cliente.html', dados)


@login_required
def listar_clientes(request):
    ordem = request.GET.get('ordem')
    nome_da_pesquisa = request.GET.get('nome_da_pesquisa', '')

    clientes = Cliente.objects.filter(
        nome__icontains=nome_da_pesquisa,
    ).order_by(Lower('nome'))

    if ordem == 'decrescente':
        clientes = Cliente.objects.filter(
            nome__icontains=nome_da_pesquisa,
        ).order_by(Lower('nome').desc())

    dados = {
        'clientes': clientes,
        'nome_da_pesquisa': nome_da_pesquisa,
    }

    return render(request, 'listar_clientes.html', dados)


@login_required
def editar_cliente(request, id):

    cliente = get_object_or_404(Cliente, id=id)

    form = ClienteForm(instance=cliente)

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)

        if form.is_valid():
            cliente = form.save()

            messages.success(
                request,
                f'Cliente {cliente.nome} alterado com sucesso!',
            )

            return redirect('listar_clientes')

    dados = {
        'formulario': form
    }

    return render(request, 'editar_cliente.html', dados)


@login_required
def excluir_cliente(request, id):

    cliente = get_object_or_404(Cliente, id=id)

    reservas_ativas = Reserva.objects.filter(
        cliente=cliente,
        status__in=['P', 'A'],
    )
    if reservas_ativas.exists():
        messages.error(
            request,
            f'Não é possível excluir o cliente {cliente.nome} {cliente.sobrenome} '
            'pois ele possui reservas pendentes ou em andamento.'
        )
        return redirect('listar_clientes')

    nome = cliente.nome
    sobrenome = cliente.sobrenome

    cliente.delete()

    mensagem = f'Cliente {nome} {sobrenome} Excluído com sucesso'
    messages.success(request, mensagem)

    return redirect('listar_clientes')


@login_required
def reservar_veiculo(request):
    form = ReservaForm()

    veiculos = Veiculo.objects.filter(status='D')

    if request.method == 'POST':
        form = ReservaForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                veiculo = Veiculo.objects.select_for_update().get(
                    pk=form.cleaned_data['veiculo'].pk,
                )
                if veiculo.status != 'D':
                    form.add_error(
                        'veiculo', 'Este veículo não está mais disponível.')
                else:
                    reserva = form.save()
                    veiculo.status = 'R'
                    veiculo.save(update_fields=['status'])

            if not form.errors:
                messages.success(
                    request,
                    f'Reserva de {reserva.cliente} para {reserva.veiculo} cadastrada com sucesso! '
                    f'Valor total: {formatar_valor(reserva.valor_total)} '
                    f'({reserva.quantidade_dias} diária(s)).',
                )
                return redirect('listar_reservas')

    dados = {
        'formulario': form,
        'veiculos': veiculos
    }

    return render(request, 'reservar_veiculo.html', dados)


@login_required
def listar_reservas(request):
    ordem = request.GET.get('ordem')
    nome_da_pesquisa = request.GET.get('nome_da_pesquisa', '')

    reservas = Reserva.objects.select_related('cliente', 'veiculo', 'devolucao')

    if nome_da_pesquisa:
        reservas = reservas.filter(
            Q(cliente__nome__icontains=nome_da_pesquisa)
            | Q(veiculo__placa__icontains=nome_da_pesquisa)
        )

    ordenacao = [Lower('cliente__nome'), Lower('cliente__sobrenome')]
    if ordem == 'decrescente':
        ordenacao = [Lower('cliente__nome').desc(),
                     Lower('cliente__sobrenome').desc()]

    reservas = reservas.order_by(*ordenacao)

    dados = {
        'reservas': reservas,
        'nome_da_pesquisa': nome_da_pesquisa,
    }
    return render(request, 'listar_reservas.html', dados)


@login_required
def editar_reserva(request, id):

    reserva = get_object_or_404(Reserva, id=id)
    if reserva.status != 'P':
        messages.error(
            request, 'Somente reservas pendentes podem ser editadas.')
        return redirect('listar_reservas')

    form = ReservaForm(instance=reserva)

    if request.method == 'POST':
        form = ReservaForm(request.POST, instance=reserva)

        if form.is_valid():
            reserva = form.save()

            messages.success(
                request,
                f'Reserva de {reserva.cliente} para {reserva.veiculo} alterada com sucesso! '
                f'Valor total: {formatar_valor(reserva.valor_total)} '
                f'({reserva.quantidade_dias} diária(s)).',
            )

            return redirect('listar_reservas')

    dados = {
        'formulario': form
    }

    return render(request, 'editar_reserva.html', dados)


@login_required
def cancelar_reserva(request, id):

    reserva = get_object_or_404(Reserva, id=id)
    if reserva.status != 'P':
        messages.error(
            request, 'Somente reservas pendentes podem ser canceladas.')
        return redirect('listar_reservas')

    reserva.status = 'X'
    reserva.save(update_fields=['status'])
    reserva.veiculo.status = 'D'
    reserva.veiculo.save(update_fields=['status'])

    messages.success(
        request,
        f'Reserva de {reserva.cliente} para {reserva.veiculo} cancelada com sucesso!',
    )

    return redirect('listar_reservas')


@login_required
def listar_veiculos_disponiveis(request):
    ordem = request.GET.get('ordem')
    nome_da_pesquisa = request.GET.get('nome_da_pesquisa', '')
    categoria_pesquisa = request.GET.get('categoria_pesquisa', '')
    status_pesquisa = request.GET.get('status_pesquisa', 'D')

    veiculos = Veiculo.objects.filter(
        modelo__icontains=nome_da_pesquisa,
        categoria__icontains=categoria_pesquisa,
        status__icontains=status_pesquisa,
    ).order_by(Lower('modelo'))

    if ordem == 'decrescente':
        veiculos = Veiculo.objects.filter(
            modelo__icontains=nome_da_pesquisa,
            categoria__icontains=categoria_pesquisa,
            status__icontains=status_pesquisa,
        ).order_by(Lower('modelo').desc())

    dados = {
        'veiculos': veiculos,
        'nome_da_pesquisa': nome_da_pesquisa,
        'categoria_pesquisa': categoria_pesquisa,
        'status_pesquisa': status_pesquisa,
        'categorias': CATEGORIA_CHOICES,
        'status_opcoes': STATUS_CHOICES,
        'ordem': ordem,
        'parametros_filtro': request.GET.urlencode(),
    }

    return render(request, 'listar_veiculos_disponiveis.html', dados)


@admin_required
def listar_manutencoes(request):

    manutencoes = Manutencao.objects.select_related('veiculo')

    dados = {
        'em_andamento': manutencoes.filter(
            data_conclusao__isnull=True).order_by('previsao_conclusao'),
        'concluidas': manutencoes.filter(
            data_conclusao__isnull=False).order_by('-data_conclusao'),
    }

    return render(request, 'listar_manutencoes.html', dados)


@admin_required
def registrar_manutencao(request):
    form = ManutencaoForm()

    if request.method == 'POST':
        form = ManutencaoForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                manutencao = form.save()
                veiculo = manutencao.veiculo
                veiculo.status = 'M'
                veiculo.save(update_fields=['status'])

            messages.success(
                request,
                f'Veículo {veiculo} enviado para manutenção.',
            )

            return redirect('listar_manutencoes')

    dados = {
        'formulario': form
    }

    return render(request, 'registrar_manutencao.html', dados)


@admin_required
@require_POST
def concluir_manutencao(request, id):

    with transaction.atomic():
        manutencao = get_object_or_404(
            Manutencao.objects.select_for_update().select_related('veiculo'),
            id=id,
        )

        if manutencao.data_conclusao:
            messages.error(request, 'Esta manutenção já foi concluída.')
            return redirect('listar_manutencoes')

        manutencao.data_conclusao = timezone.now()
        manutencao.save(update_fields=['data_conclusao'])

        veiculo = manutencao.veiculo
        veiculo.status = 'D'
        veiculo.save(update_fields=['status'])

    messages.success(
        request,
        f'Manutenção concluída. Veículo {veiculo} disponível novamente.',
    )

    return redirect('listar_manutencoes')


@admin_required
def configurar_tarifas(request):
    form = TarifaForm()

    if request.method == 'POST':
        form = TarifaForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                form.save()

            messages.success(request, 'Tarifas salvas com sucesso!')

            return redirect('configurar_tarifas')

    dados = {
        'formulario': form
    }

    return render(request, 'configurar_tarifas.html', dados)


@login_required
def registrar_retirada(request):
    ordem = request.GET.get('ordem')
    nome_da_pesquisa = request.GET.get('nome_da_pesquisa', '')

    reservas = Reserva.objects.select_related(
        'cliente', 'veiculo'
    ).filter(
        status='P',
        veiculo__status='R',
        retirada__isnull=True,
    )

    if nome_da_pesquisa:
        reservas = reservas.filter(
            Q(cliente__nome__icontains=nome_da_pesquisa)
            | Q(veiculo__placa__icontains=nome_da_pesquisa)
        )

    ordenacao = [Lower('cliente__nome'), Lower('cliente__sobrenome')]
    if ordem == 'decrescente':
        ordenacao = [Lower('cliente__nome').desc(),
                     Lower('cliente__sobrenome').desc()]

    reservas = reservas.order_by(*ordenacao)

    dados = {
        'reservas': reservas,
        'nome_da_pesquisa': nome_da_pesquisa,
    }
    return render(request, 'registrar_retirada.html', dados)


@login_required
def confirmar_retirada(request, id):

    reserva = get_object_or_404(
        Reserva.objects.select_related('cliente', 'veiculo').filter(
            status='P',
            veiculo__status='R',
            retirada__isnull=True,
        ),
        id=id,
    )
    retirada = Retirada(reserva=reserva)

    form = ConfirmarRetiradaForm(instance=retirada)

    if request.method == 'POST':
        form = ConfirmarRetiradaForm(request.POST, instance=retirada)

        if form.is_valid():
            try:
                form.save()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(
                    request,
                    f'Retirada do veículo {reserva.veiculo} para '
                    f'{reserva.cliente} confirmada com sucesso!',
                )

                return redirect('listar_reservas')

    dados = {
        'formulario': form,
        'reserva': reserva,
    }

    return render(request, 'confirmar_retirada.html', dados)


@login_required
def registrar_devolucao(request):
    ordem = request.GET.get('ordem')
    nome_da_pesquisa = request.GET.get('nome_da_pesquisa', '')

    reservas = Reserva.objects.select_related(
        'cliente', 'veiculo'
    ).filter(
        status='A',
        retirada__isnull=False,
        devolucao__isnull=True,
    )

    if nome_da_pesquisa:
        reservas = reservas.filter(
            Q(cliente__nome__icontains=nome_da_pesquisa)
            | Q(veiculo__placa__icontains=nome_da_pesquisa)
        )

    ordenacao = [Lower('cliente__nome'), Lower('cliente__sobrenome')]
    if ordem == 'decrescente':
        ordenacao = [Lower('cliente__nome').desc(),
                     Lower('cliente__sobrenome').desc()]

    reservas = reservas.order_by(*ordenacao)

    dados = {
        'reservas': reservas,
        'nome_da_pesquisa': nome_da_pesquisa,
    }
    return render(request, 'registrar_devolucao.html', dados)


@login_required
def confirmar_devolucao(request, id):

    reserva = get_object_or_404(
        Reserva.objects.select_related('cliente', 'veiculo', 'retirada').filter(
            status='A',
            retirada__isnull=False,
            devolucao__isnull=True,
        ),
        id=id,
    )
    devolucao = Devolucao(reserva=reserva)

    form = ConfirmarDevolucaoForm(instance=devolucao)

    if request.method == 'POST':
        form = ConfirmarDevolucaoForm(request.POST, instance=devolucao)

        if form.is_valid():
            try:
                form.save()
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(
                    request,
                    f'Devolução do veículo {reserva.veiculo} por '
                    f'{reserva.cliente} registrada com sucesso!',
                )

                return redirect('listar_reservas')

    dados = {
        'formulario': form,
        'reserva': reserva,
    }

    return render(request, 'confirmar_devolucao.html', dados)
