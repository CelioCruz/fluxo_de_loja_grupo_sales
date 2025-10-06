import streamlit as st
import base64
import json
import bcrypt
from datetime import datetime
from zoneinfo import ZoneInfo
import importlib
import logging
import sys
import os

# Adiciona o diretório atual ao caminho para imports locais
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema de Atendimento", layout="centered")

# --- CONFIGURAÇÃO DE LOG ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FUNÇÃO PARA FUNDO ---
def set_fundo_cor_solido():
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f0f4e2;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

set_fundo_cor_solido()

# --- ESTADO INICIAL ---
if 'etapa' not in st.session_state:
    st.session_state.etapa = 'login'
if 'loja' not in st.session_state:
    st.session_state.loja = ''
if 'subtela' not in st.session_state:
    st.session_state.subtela = ''
if 'nome_atendente' not in st.session_state:
    st.session_state.nome_atendente = ''
if 'horario_entrada' not in st.session_state:
    st.session_state.horario_entrada = None
if 'horario_saida' not in st.session_state:
    st.session_state.horario_saida = None

# === CONEXÃO COM GOOGLE SHEETS (ANTES DE TUDO) ===
try:
    from google_planilha import GooglePlanilha
    if 'gsheets' not in st.session_state:
        st.session_state.gsheets = GooglePlanilha()
        logger.info("✅ Conexão com Google Sheets estabelecida.")
except ModuleNotFoundError:
    st.error("❌ Arquivo 'google_planilha.py' não encontrado. Verifique o nome e localização.")
    st.stop()
except Exception as e:
    st.error("❌ Falha ao conectar ao Google Sheets")
    st.exception(e)
    st.stop()

# 🔹 Função global: atualiza reservas expiradas
def atualizar_reservas():
    """Executa limpeza de reservas antigas. Deve ser chamada após ter gsheets."""
    agora = datetime.now()
    ultima_execucao = st.session_state.get("ultima_limpeza_reservas", None)
    
    # Evita executar mais de uma vez por minuto
    if ultima_execucao and (agora - ultima_execucao).total_seconds() < 60:
        return

# --- TELA DE LOGIN ---
def tl_login():
    st.markdown("<h1 style='text-align: center; color: #1f77b4;'>🔐 ACESSO AO SISTEMA</h1>", unsafe_allow_html=True)
    st.subheader("Autenticação de Usuário")

    # Carregar usuários do JSON
    try:
        with open("usuarios.json", "r", encoding="utf-8") as f:
            dados = json.load(f)
            usuarios = {u["login"].upper(): u for u in dados["usuarios"]}
    except FileNotFoundError:
        st.error("❌ Arquivo de usuários não encontrado. Contate o administrador.")
        return
    except Exception as e:
        st.error(f"❌ Erro ao carregar usuários: {str(e)}")
        return

    # Formulário de login
    nome = st.text_input("Usuário").upper()
    senha = st.text_input("Senha", type="password")

    if st.button("✅ ENTRAR NO SISTEMA", use_container_width=True):
        if nome in usuarios:
            usuario = usuarios[nome]
            senha_hash = usuario["senha_hash"].encode()
            if bcrypt.checkpw(senha.encode(), senha_hash):
                st.session_state.nome_atendente = nome
                st.session_state.etapa = 'loja'
                st.session_state.horario_entrada = datetime.now()
                st.success(f"✅ Bem-vindo, {nome}!")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Senha incorreta.")
        else:
            st.error("❌ Usuário não encontrado.")

    # Botão: Fechar Sistema
    if st.button("❌ FECHAR SISTEMA", use_container_width=True, type="secondary"):
        st.session_state.horario_saida = datetime.now()
        st.markdown("### 🖐️ Sessão encerrada")
        entrada = st.session_state.horario_entrada.strftime("%d/%m/%Y às %H:%M:%S") if st.session_state.horario_entrada else "Não registrado"
        saida = st.session_state.horario_saida.strftime("%d/%m/%Y às %H:%M:%S")
        st.info(f"**Entrada:** {entrada}\n\n**Saída:** {saida}")
        st.success("Obrigado por usar o sistema! Você pode fechar a aba.")
        st.stop()

# --- CARREGAMENTO DAS TELAS PRINCIPAIS ---
try:
    from loja_select import tl_loja
except Exception as e:
    st.error("❌ Falha ao carregar loja_select.py")
    st.exception(e)
    st.stop()

try:
    from tl_atendimento import tl_atendimento_principal
except Exception as e:
    st.error("❌ Falha ao carregar tl_atendimento.py")
    st.exception(e)
    st.stop()

# --- CARREGAMENTO DAS SUBTELAS (com importlib) ---
SUBTELAS = {}
modulos_subtelas = [
    'tl_receita',
    'tl_pesquisa',
    'tl_exame',
    'tl_reserva',
    'tl_sem_receita',
    'tl_ex_vista',
    'tl_exame',
    'tl_ajuste',
    'tl_entrega',
    'tl_garantia',   
]

for nome_modulo in modulos_subtelas:
    try:
        module = importlib.import_module(nome_modulo)

        # Procura função com padrão: tl_nome → função `tl_nome` ou `mostrar` ou `nome`
        func = None
        chave = nome_modulo.replace('tl_', '')

        if hasattr(module, nome_modulo):
            func = getattr(module, nome_modulo)
        elif hasattr(module, 'mostrar'):
            func = module.mostrar
        elif hasattr(module, chave):
            func = getattr(module, chave)

        if func:
            SUBTELAS[chave] = func
            logger.info(f"✅ Função '{func.__name__}' carregada de {nome_modulo}.py")
        else:
            logger.warning(f"⚠️ Nenhuma função encontrada em {nome_modulo}.py")
            def erro():
                st.error(f"❌ Falha ao carregar `{nome_modulo}.py`: função não encontrada.")
            SUBTELAS[chave] = erro

    except ModuleNotFoundError:
        st.error(f"❌ Módulo não encontrado: `{nome_modulo}.py`. Verifique o nome do arquivo.")
    except Exception as e:
        logger.error(f"❌ Falha ao carregar {nome_modulo}: {e}")
        def erro():
            st.error(f"❌ Erro ao carregar `{nome_modulo}.py`")
        SUBTELAS[nome_modulo.replace('tl_', '')] = erro

# === NAVEGAÇÃO ENTRE TELAS ===
if st.session_state.etapa == 'login':
    tl_login()

elif st.session_state.etapa == 'loja':
    atualizar_reservas()
    tl_loja()

elif st.session_state.etapa == 'atendimento':
    atualizar_reservas()
    tl_atendimento_principal()

elif st.session_state.etapa == 'subtela':
    atualizar_reservas()
    nome_subtela = st.session_state.subtela
    if nome_subtela in SUBTELAS:
        SUBTELAS[nome_subtela]()
    else:
        st.error("❌ Tela não encontrada.")
        if st.button("Voltar ao início", key="btn_voltar_inicio"):
            st.session_state.etapa = 'login'
            st.rerun()

else:
    st.error("⚠️ Etapa inválida.")
    st.session_state.etapa = 'login'
    st.rerun()

# --- SIDEBAR: Informações do usuário e logout ---
st.sidebar.title("🧭 Navegação")
if st.session_state.horario_entrada:
    horario_formatado = st.session_state.horario_entrada.strftime("%H:%M:%S")
    st.sidebar.markdown(f"**🕒 Entrada:** {horario_formatado}")

if st.session_state.nome_atendente:
    st.sidebar.markdown(f"**👤 Atendente:** {st.session_state.nome_atendente}")

if st.session_state.loja:
    st.sidebar.markdown(f"**🏪 Loja:** {st.session_state.loja}")

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
    st.session_state.horario_saida = datetime.now()
    hora_saida = st.session_state.horario_saida.strftime("%d/%m/%Y às %H:%M:%S")
    
    # 🟡 Não grava no Sheets porque não há ab_loguin
    # Apenas limpa a sessão
    st.session_state.clear()
    st.success(f"✅ Você saiu às {hora_saida}.")
    st.rerun()

# --- RODAPÉ ---
st.markdown(
    "<br><hr><center>"
    "<small>💼 Projeto <strong>Leonardo Pesil</strong>, desenvolvido por <strong>Cruz.devsoft</strong> | © 2025</small>"
    "</center>",
    unsafe_allow_html=True
)