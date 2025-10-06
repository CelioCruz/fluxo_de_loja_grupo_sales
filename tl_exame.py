import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from google_planilha import GooglePlanilha  

def tl_exame():
    st.subheader("📅 CONFIRMAR EXAME OFTALMOLÓGICO")
    st.info(f"**Loja:** {st.session_state.loja}")
    st.info(f"**Usuário:** {st.session_state.nome_atendente}")
    st.markdown("---")

    # Conecta com Google Sheets
    if 'gsheets' not in st.session_state:
        try:
            st.session_state.gsheets = GooglePlanilha()
        except Exception as e:
            st.error("❌ Falha ao conectar com Google Sheets")
            st.exception(e)
            return
    gsheets = st.session_state.gsheets

    # Carrega vendedores
    try:
        vendedores_data = gsheets.get_vendedores_por_loja()
        vendedores = [v['VENDEDOR'] for v in vendedores_data] if vendedores_data else []
    except Exception as e:
        st.error(f"❌ Erro ao carregar vendedores: {e}")
        vendedores = []

    if not vendedores:
        st.warning("⚠️ Nenhum vendedor encontrado.")
        if st.button("↩️ Voltar", key="btn_voltar_consulta"):
            st.session_state.etapa = 'atendimento'
            st.rerun()
        return

    # Campos do formulário
    cliente = st.text_input("Nome do Paciente", key="cliente_consulta_input").strip().upper()
    vendedor = st.selectbox(
        "Vendedor",
        vendedores,
        index=None,
        placeholder="Selecione o vendedor",
        key="vend_consulta"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ CONFIRMAR", type="primary", key="btn_registrar_consulta"):
            if not cliente or not vendedor:
                st.error("⚠️ Preencha todos os campos!")
            else:
                # ✅ Usa horário de São Paulo
                horario_sp = datetime.now(ZoneInfo("America/Sao_Paulo"))

                dados = {
                    'loja': st.session_state.loja,
                    'vendedor': vendedor,
                    'cliente': cliente,
                    'data': horario_sp.strftime("%d/%m/%Y"),
                    'hora': horario_sp.strftime("%H:%M"),
                    'atendimento': '1',
                    'receita': '',
                    'perda': '',
                    'venda': '',
                    'reserva': '',
                    'pesquisa': '',
                    'consulta': '1',
                }

                if gsheets.registrar_atendimento(dados):
                    st.balloons()
                    st.success("✅ Consulta registrada com sucesso!")

                    # ✅ Passa dados para próxima tela
                    st.session_state.enc_cliente = cliente
                    st.session_state.enc_vendedor = vendedor

                    # Navega
                    st.session_state.etapa = 'subtela'
                    st.session_state.subtela = 'ex_vista'
                    st.rerun()
                else:
                    st.error("❌ Falha ao salvar no Google Sheets. Tente novamente.")

    with col2:
        if st.button("↩️ Voltar", key="btn_voltar_consulta"):
            # ✅ Limpa variáveis intermediárias, se necessário
            if 'enc_cliente' in st.session_state:
                del st.session_state.enc_cliente
            if 'enc_vendedor' in st.session_state:
                del st.session_state.enc_vendedor
            st.session_state.etapa = 'atendimento'
            st.rerun()