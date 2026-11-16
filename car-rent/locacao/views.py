from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Lower
from functools import wraps
from .forms import ClienteForm, FuncionarioForm, ReservaForm, VeiculoForm
from .models import CATEGORIA_CHOICES, STATUS_CHOICES, Cliente, Funcionario, Reserva, Veiculo

# Create your views here.

User = get_user_model()


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

    # TODO: quando o model de Reserva existir, bloquear a exclusão se o
    # cliente tiver reservas ativas (requisito do caso de uso).

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
            reserva = form.save()

            messages.success(
                request,
                f'Reserva de {reserva.cliente} para {reserva.veiculo} cadastrada com sucesso!',
            )
            reserva.veiculo.status = 'R'
            reserva.veiculo.save()
            return redirect('listar_reservas')

    dados = {
        'formulario': form,
        'veiculos': veiculos
    }

    return render(request, 'reservar_veiculo.html', dados)


@login_required
def listar_reservas(request):
    reservas = Reserva.objects.all()
    dados = {
        'reservas': reservas
    }
    return render(request, 'listar_reservas.html', dados)


@login_required
def editar_reserva(request, id):

    reserva = get_object_or_404(Reserva, id=id)

    form = ReservaForm(instance=reserva)

    if request.method == 'POST':
        form = ReservaForm(request.POST, instance=reserva)

        if form.is_valid():
            reserva = form.save()

            messages.success(
                request,
                f'Reserva de {reserva.cliente} para {reserva.veiculo} alterada com sucesso!',
            )

            return redirect('listar_reservas')

    dados = {
        'formulario': form
    }

    return render(request, 'editar_reserva.html', dados)


@login_required
def cancelar_reserva(request, id):

    reserva = get_object_or_404(Reserva, id=id)
    reserva.veiculo.status = 'D'
    reserva.veiculo.save()

    reserva.delete()

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
