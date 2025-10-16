import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from google_planilha import GooglePlanilha
import pandas as pd
import io

def tl_relatorio_vendedor():
    st.subheader("👨‍💼 RELATÓRIO POR VENDEDOR — HOJE")
    st.info(f"**Loja:** {st.session_state.loja}")
    st.info(f"**Usuário:** {st.session_state.nome_atendente}")
    st.markdown("---")

    if 'gsheets' not in st.session_state:
        try:
            st.session_state.gsheets = GooglePlanilha()
        except Exception as e:
            st.error("❌ Falha ao conectar com Google Sheets")
            st.exception(e)
            return
    gsheets = st.session_state.gsheets

    # Carregar vendedores da loja
    try:
        vendedores_data = gsheets.get_vendedores_por_loja()
        vendedores = [v['VENDEDOR'] for v in vendedores_data]
    except Exception as e:
        st.error("❌ Erro ao carregar vendedores")
        st.exception(e)
        return

    if not vendedores:
        st.warning("⚠️ Nenhum vendedor encontrado para esta loja.")
        if st.button("↩️ Voltar", key="btn_voltar_relatorio"):
            st.session_state.etapa = 'loja'
            st.rerun()
        return

    # Seleção de vendedor
    vendedor = st.selectbox(
        "Vendedor",
        vendedores,
        index=None,
        placeholder="Selecione o vendedor",
        key="vend_relatorio_hoje"
    )

    if not vendedor:
        st.info("🔍 Selecione um vendedor para visualizar os registros de **hoje**.")
        if st.button("↩️ Voltar", key="btn_voltar_relatorio_sem_vend"):
            st.session_state.etapa = 'loja'
            st.rerun()
        return

    # ✅ Usa horário de São Paulo para definir "hoje"
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    # Buscar registros da planilha
    try:
        todos_registros = gsheets.aba_relatorio.get_all_records()
    except Exception as e:
        st.error("❌ Erro ao carregar os dados da planilha")
        st.exception(e)
        return

    if not todos_registros:
        st.info("📭 Nenhum dado encontrado na planilha de relatórios.")
        if st.button("↩️ Voltar", key="btn_voltar_relatorio_sem_dados"):
            st.session_state.etapa = 'loja'
            st.rerun()
        return

    # Identificar colunas essenciais
    col_loja = col_vend = col_data = None
    for k in todos_registros[0].keys():
        k_low = k.strip().lower()
        if k_low in ['loja', 'unidade', 'filial']:
            col_loja = k
        if k_low in ['vendedor', 'vendedora', 'funcionário', 'vend']:
            col_vend = k
        if k_low in ['data', 'datas', 'dt']:
            col_data = k

    if not col_loja or not col_vend or not col_data:
        st.error("❌ Colunas 'Loja', 'Vendedor' ou 'Data' não encontradas.")
        if st.button("↩️ Voltar", key="btn_voltar_relatorio_sem_colunas"):
            st.session_state.etapa = 'loja'
            st.rerun()
        return

    # Filtrar registros: mesma loja + mesmo vendedor + data = hoje (SP)
    dados_filtrados = []
    for r in todos_registros:
        if str(r.get(col_loja, "")).strip().lower() != st.session_state.loja.strip().lower():
            continue
        if str(r.get(col_vend, "")).strip().lower() != vendedor.strip().lower():
            continue
        try:
            data_row = datetime.strptime(str(r.get(col_data, "")).strip(), "%d/%m/%Y").date()
        except (ValueError, TypeError):
            continue
        if data_row == hoje:
            dados_filtrados.append(r)

    if not dados_filtrados:
        st.info(f"📭 Nenhum registro encontrado para **{vendedor}** em **{hoje.strftime('%d/%m/%Y')}**.")
    else:
        df = pd.DataFrame(dados_filtrados)

        # Mapear colunas desejadas
        colunas_desejadas = {
            "DATA": ["data", "dt"],
            "LOJA": ["loja", "unidade", "filial"],
            "CLIENTE": ["cliente", "nome"],
            "RECEITA": ["receita", "faturamento"],
            "VENDA": ["venda", "pedidos"],
            "PERDA": ["perda", "cancelamentos"],
            "RESERVA": ["reserva", "agendamento"]
        }

        colunas_finais = {}
        for nome, palavras in colunas_desejadas.items():
            for col in df.columns:
                if any(p in col.lower() for p in palavras):
                    colunas_finais[col] = nome
                    break

        if colunas_finais:
            df = df[list(colunas_finais.keys())].rename(columns=colunas_finais)

        ordem = ["DATA", "LOJA", "CLIENTE", "RECEITA", "VENDA", "PERDA", "RESERVA"]
        colunas_existentes = [c for c in ordem if c in df.columns]
        df = df[colunas_existentes].copy()

        # Limpeza numérica
        colunas_numericas = ["RECEITA", "VENDA", "PERDA", "RESERVA"]
        for col in colunas_numericas:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace(
                    ["", "nan", "None", "NaN", "null", "–", "-", " ", "R$", "R$ ", "r$", "r$ "], "0"
                )
                df[col] = df[col].str.replace(r"[^\d.,-]", "", regex=True)
                df[col] = df[col].str.replace(",", ".", regex=False)
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Exibir tabela
        st.markdown("### Registros de Hoje")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Resumo
        st.markdown("### Resumo (Hoje)")
        col1, col2, col3, col4 = st.columns(4)
        receita_total = int(df["RECEITA"].sum()) if "RECEITA" in df.columns else 0
        venda_total = int(df["VENDA"].sum()) if "VENDA" in df.columns else 0
        perda_total = int(df["PERDA"].sum()) if "PERDA" in df.columns else 0
        reserva_total = int(df["RESERVA"].sum()) if "RESERVA" in df.columns else 0

        col1.metric("Receitas", str(receita_total))
        col2.metric("Vendas", str(venda_total))
        col3.metric("Perdas", str(perda_total))
        col4.metric("Reservas", str(reserva_total))

        # Botão de download
        try:
            buffer = io.BytesIO()
            df.to_excel(buffer, index=False, engine="openpyxl")
            st.download_button(
                label="📥 Baixar como Excel",
                data=buffer.getvalue(),
                file_name=f"Relatorio_Hoje_{vendedor.replace(' ', '_')}_{st.session_state.loja}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_relatorio_hoje"
            )
        except Exception as e:
            st.error(f"Erro ao gerar Excel: {e}")

    # Botão Voltar
    if st.button("↩️ VOLTAR", key="btn_voltar_relatorio_final"):
        st.session_state.etapa = 'loja'
        st.rerun()