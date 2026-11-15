from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', login_required(TemplateView.as_view(
        template_name='home.html')), name='home'),
    path('funcionarios/', views.listar_funcionarios, name='listar_funcionarios'),
    path('funcionarios/cadastrar/', views.cadastrar_funcionario,
         name='cadastrar_funcionario'),
    path('funcionarios/inativos/', views.funcionarios_inativos,
         name='funcionarios_inativos'),
    path('funcionarios/<int:id>/editar/',
         views.editar_funcionario, name='editar_funcionario'),
    path('funcionarios/<int:id>/excluir/',
         views.excluir_funcionario, name='excluir_funcionario'),
    path('funcionarios/<int:id>/ativar/',
         views.ativar_funcionario, name='ativar_funcionario'),
    path('funcionarios/<int:id>/desativar/',
         views.desativar_funcionario, name='desativar_funcionario'),
    path('veiculos/cadastrar/', views.cadastrar_veiculo, name='cadastrar_veiculo'),
    path('veiculos/', views.listar_veiculos, name='listar_veiculos'),
    path('veiculos/<int:id>/editar/', views.editar_veiculo, name='editar_veiculo'),
    path('veiculos/<int:id>/excluir/',
         views.excluir_veiculo, name='excluir_veiculo'),
    path('clientes/', views.listar_clientes, name='listar_clientes'),
    path('clientes/cadastrar/', views.cadastrar_cliente,
         name='cadastrar_cliente'),
    path('clientes/<int:id>/editar/',
         views.editar_cliente, name='editar_cliente'),
    path('clientes/<int:id>/excluir/',
         views.excluir_cliente, name='excluir_cliente'),
]
