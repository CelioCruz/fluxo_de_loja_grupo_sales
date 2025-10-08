import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from typing import Dict, List, Optional
import streamlit as st
import os
import json
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dateutil import parser
import re

# 🔹 Constantes
SPREADSHEET_NAME = "fluxo de loja"
BACKUP_AGE_DAYS = 3 * 365.25  # 3 anos
CLEANUP_BACKUP_OLDER_THAN_DAYS = 5 * 365.25  # 5 anos
DEFAULT_TIMEZONE = ZoneInfo("America/Sao_Paulo")

# ✅ Escopos CORRETOS — SEM ESPAÇOS!
SCOPES_SHEETS = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly'
]
SCOPES_DRIVE = [
    'https://www.googleapis.com/auth/drive'
]


def _get_credentials():
    """Obtém credenciais de variáveis de ambiente (Render) ou st.secrets (local)."""
    if 'GCP_PROJECT_ID' in os.environ:
        # Render: usa variáveis de ambiente
        return {
            "type": "service_account",
            "project_id": os.environ["GCP_PROJECT_ID"],
            "private_key_id": os.environ["GCP_PRIVATE_KEY_ID"],
            "private_key": os.environ["GCP_PRIVATE_KEY"].replace("\\n", "\n"),
            "client_email": os.environ["GCP_CLIENT_EMAIL"],
            "client_id": os.environ["GCP_CLIENT_ID"],
            "client_x509_cert_url": os.environ["GCP_CLIENT_X509_CERT_URL"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.environ["GCP_CLIENT_X509_CERT_URL"]
            
        }
    else:
        # Local: usa secrets.toml
        return st.secrets["gcp_service_account"]


class GooglePlanilha:
    """
    Classe para integração com Google Sheets e Drive.
    Funciona tanto localmente quanto no Render.
    """

    def __init__(self):
        """Inicializa a conexão com o Google Sheets."""
        self.credentials_dict = _get_credentials()
        self.client = self._criar_conexao()
        
        try:
            self.planilha = self.client.open(SPREADSHEET_NAME)
        except SpreadsheetNotFound:
            st.error("❌ Planilha 'fluxo de loja' não encontrada.")
            st.markdown(f"💡 Compartilhe com: `{self.credentials_dict['client_email']}` como **Editor**.")
            st.stop()

        # Abas principais — NOMES EXATOS DA SUA PLANILHA
        self.aba_vendedores = self._get_worksheet("ab_vendedor")
        self.aba_dados = self._get_worksheet("ab_dados")

        # Verifica estrutura e configuração
        self._verificar_estrutura()
        self._criar_aba_config()

    def _criar_conexao(self):
        try:
            client = gspread.service_account_from_dict(self.credentials_dict, scopes=SCOPES_SHEETS)
            return client
        except Exception as e:
            st.error(f"❌ Falha ao conectar ao Google Sheets: {e}")
            st.stop()

    def _get_worksheet(self, name: str):
        """Retorna worksheet ou None se não existir."""
        try:
            return self.planilha.worksheet(name)
        except WorksheetNotFound:
            st.warning(f"⚠️ Aba '{name}' não encontrada.")
            return None

    def _verificar_estrutura(self):
        """Verifica cabeçalhos da aba 'ab_dados'."""
        if self.aba_dados is None:
            st.warning("⚠️ Aba 'ab_dados' não disponível. Não foi possível verificar a estrutura.")
            return

        try:
            cabecalhos = [str(c).strip() for c in self.aba_dados.row_values(1)]
            esperados = [
                'LOJA', 'DATA', 'HORA', 'VENDEDOR', 'CLIENTE', 'ATENDIMENTO', 'RECEITA',
                'PERDA', 'VENDA', 'RESERVA', 'PESQUISA', 'EXAME DE VISTA', 'GAR_LENTE',
                'GAR_ARMACAO', 'AJUSTE', 'ENTREGA'
            ]

            if len(cabecalhos) < len(esperados):
                st.warning(f"⚠️ Número insuficiente de colunas. Esperado: {len(esperados)}, Encontrado: {len(cabecalhos)}")
                return

            if cabecalhos[:len(esperados)] != esperados:
                st.warning("⚠️ Estrutura da aba 'ab_dados' incorreta.")
            else:
                st.success("✅ Estrutura da aba 'ab_dados' validada.")

        except Exception as e:
            st.error(f"❌ Erro ao verificar estrutura: {e}")

    def _criar_aba_config(self):
        """Cria aba 'Config' se não existir."""
        try:
            self.planilha.worksheet("Config")
        except WorksheetNotFound:
            aba = self.planilha.add_worksheet("Config", rows="10", cols="5")
            aba.update("A1:B2", [["Último Backup", "Data"], ["backup_3_anos", ""]])
            st.success("✅ Aba 'Config' criada.")

    # === BACKUP AUTOMÁTICO ===

    def _obter_data_ultimo_backup(self) -> Optional[datetime]:
        try:
            aba = self.planilha.worksheet("Config")
            valor = aba.acell("B2").value
            return datetime.strptime(valor, "%Y-%m-%d") if valor else None
        except Exception:
            return None

    def _registrar_data_backup(self, data: datetime):
        try:
            aba = self.planilha.worksheet("Config")
            aba.update("B2", data.strftime("%Y-%m-%d"))
        except Exception as e:
            st.error(f"❌ Falha ao registrar data do backup: {e}")

    def _deve_fazer_backup(self) -> bool:
        ultimo = self._obter_data_ultimo_backup()
        if ultimo is None:
            return True
        return (datetime.now() - ultimo).days >= BACKUP_AGE_DAYS

    def rodar_backup_automatico(self):
        if not self._deve_fazer_backup():
            return

        try:
            df = pd.DataFrame(self.aba_dados.get_all_records())
            if df.empty:
                st.info("📭 Nenhum dado para backup.")
                return

            nome_arquivo = f"backup_ab_dados_{datetime.now().strftime('%Y-%m-%d')}.csv"
            csv = df.to_csv(index=False)

            self._salvar_no_drive(nome_arquivo, csv)
            self._registrar_data_backup(datetime.now())
            self._limpar_aba_dados()
            self._limpar_backups_antigos_no_drive()

        except Exception as e:
            st.warning(f"⚠️ Falha no backup: {e}")

    def _salvar_no_drive(self, nome_arquivo: str, conteudo: str):
        try:
            credentials = service_account.Credentials.from_service_account_info(
                self.credentials_dict,
                scopes=SCOPES_DRIVE
            )
            service = build("drive", "v3", credentials=credentials)

            media = MediaIoBaseUpload(BytesIO(conteudo.encode()), mimetype='text/csv')
            file_metadata = {'name': nome_arquivo}
            file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()

            st.success(f"✅ Backup salvo: `{nome_arquivo}` (ID: {file['id']})")
        except Exception as e:
            st.error(f"❌ Falha ao salvar no Drive: {e}")

    def _limpar_aba_dados(self):
        try:
            if self.aba_dados is None:
                return
            cabecalhos = self.aba_dados.row_values(1)
            self.aba_dados.clear()
            self.aba_dados.update("A1", [cabecalhos])
            st.info("🧹 Dados da aba 'ab_dados' limpos.")
        except Exception as e:
            st.error(f"❌ Falha ao limpar aba: {e}")

    def _limpar_backups_antigos_no_drive(self):
        try:
            credentials = service_account.Credentials.from_service_account_info(
                self.credentials_dict,
                scopes=SCOPES_DRIVE
            )
            service = build("drive", "v3", credentials=credentials)

            query = "mimeType='text/csv' and trashed=false and name contains 'backup_ab_dados_'"
            results = service.files().list(q=query, fields="files(id, name)").execute()
            files = results.get("files", [])

            agora = datetime.now()
            for file in files:
                match = re.search(r"backup_ab_dados_(\d{4}-\d{2}-\d{2})\.csv", file["name"])
                if match:
                    data_arquivo = datetime.strptime(match.group(1), "%Y-%m-%d")
                    if (agora - data_arquivo).days > CLEANUP_BACKUP_OLDER_THAN_DAYS:
                        service.files().delete(fileId=file["id"]).execute()
                        st.warning(f"🗑️ Backup antigo removido: `{file['name']}`")
        except Exception as e:
            st.error(f"❌ Erro ao limpar backups antigos: {e}")

    # === MÉTODOS PÚBLICOS ===

    def get_all_records(self) -> List[Dict]:
        try:
            return self.aba_dados.get_all_records() if self.aba_dados else []
        except Exception as e:
            st.error(f"❌ Falha ao ler registros: {e}")
            return []

    def get_vendedores_por_loja(self, loja: str = None) -> List[Dict]:
        try:
            if 'vendedores_cache' not in st.session_state:
                coluna_a = self.aba_vendedores.col_values(1) if self.aba_vendedores else []
                st.session_state.vendedores_cache = [
                    {"VENDEDOR": nome.strip()} for nome in coluna_a if nome.strip()
                ]
            return st.session_state.vendedores_cache
        except Exception as e:
            st.error(f"❌ Falha ao buscar vendedores: {e}")
            return []

    def registrar_atendimento(self, dados: Dict) -> bool:
        try:
            for campo in ['loja', 'vendedor', 'cliente']:
                if not dados.get(campo):
                    st.error(f"❌ {campo.upper()} é obrigatório.")
                    return False

            dados['hora'] = dados.get('hora') or datetime.now(DEFAULT_TIMEZONE).strftime("%H:%M:%S")

            mapeamento = [
                ('loja', 'LOJA'), ('data', 'DATA'), ('hora', 'HORA'),
                ('vendedor', 'VENDEDOR'), ('cliente', 'CLIENTE'),
                ('atendimento', 'ATENDIMENTO'), ('receita', 'RECEITA'),
                ('perda', 'PERDA'), ('venda', 'VENDA'), ('reserva', 'RESERVA'),
                ('pesquisa', 'PESQUISA'), ('consulta', 'EXAME DE VISTA'), ('gar_lente', 'GAR_LENTE'),
                ('gar_arma', 'GAR_ARMACAO'), ('ajuste', 'AJUSTE'), ('entrega', 'ENTREGA')
            ]

            valores = [str(dados.get(campo, '')).strip() for campo, _ in mapeamento]
            self.aba_dados.append_row(valores, value_input_option='USER_ENTERED')
            return True

        except Exception as e:
            st.error(f"❌ Falha ao salvar: {e}")
            return False