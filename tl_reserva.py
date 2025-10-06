import streamlit as st
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google_planilha import GooglePlanilha 


def tl_reserva():
    st.subheader("📦 RESERVAS ACUMULADAS")
    st.info(f"**Loja:** {st.session_state.loja}")
    st.info(f"**Atendente:** {st.session_state.nome_atendente}")
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
        vendedores = [v['VENDEDOR'] for v in vendedores_data]
    except Exception as e:
        st.error(f"❌ Erro ao carregar vendedores: {e}")
        vendedores = []

    if not vendedores:
        st.warning("⚠️ Nenhum vendedor encontrado.")
        if st.button("↩️ Voltar", key="btn_voltar_reservas"):
            st.session_state.etapa = 'atendimento'
            st.rerun()
        return

    # Seleciona vendedor
    vendedor = st.selectbox(
        "Vendedor",
        vendedores,
        index=None,
        placeholder="Selecione o vendedor",
        key="vend_reservas"
    )

    # Campo: Cliente
    cliente_input = st.text_input("Nome do Cliente", key="cliente_reservas_input")
    cliente = cliente_input.strip().upper() if cliente_input else ""

    # === ESCOLHA DE TIPO: CONVERSÃO OU DESISTÊNCIA ===
    st.markdown("### 🔘 Selecione o tipo de registro:")

    cols = st.columns(2)

    with cols[0]:
        if st.button("✅ CONVERSÃO", use_container_width=True, type="primary", key="btn_tipo_venda"):
            if not vendedor or not cliente:
                st.error("⚠️ Preencha o vendedor e o cliente!")
                return
            st.session_state.tipo_reserva = "CONVERSÃO"
            st.session_state.cliente_reserva = cliente
            st.session_state.vendedor_reserva = vendedor
            st.rerun()

    with cols[1]:
        if st.button("❌ DESISTÊNCIA", use_container_width=True, type="secondary", key="btn_tipo_perda"):
            if not vendedor or not cliente:
                st.error("⚠️ Preencha o vendedor e o cliente!")
                return
            st.session_state.tipo_reserva = "DESISTÊNCIA"
            st.session_state.cliente_reserva = cliente
            st.session_state.vendedor_reserva = vendedor
            st.rerun()

    # Verifica se o tipo foi escolhido
    if 'tipo_reserva' not in st.session_state:
        st.warning("⚠️ Por favor, escolha o tipo de registro acima.")
        return

    # === MOSTRA CONFIRMAÇÃO DO TIPO ESCOLHIDO ===
    tipo = st.session_state.tipo_reserva
    cli = st.session_state.cliente_reserva
    vend = st.session_state.vendedor_reserva

    st.markdown("---")
    st.success(f"✅ **CONFIRMADO**: {cli} | **Tipo:** {tipo} | Vendedor: {vend}")

    # ✅ VALIDAÇÃO: Verifica se o cliente tem reserva nos últimos 30 dias
    if st.button("✅ REGISTRAR RESERVA", type="primary", use_container_width=True, key="btn_registrar_reserva"):
        if not vend or not cli:
            st.error("⚠️ Preencha todos os campos!")
            return

        # ✅ Tudo certo: pode registrar
        horario_sp = datetime.now(ZoneInfo("America/Sao_Paulo"))

        dados_registro = {
            'loja': st.session_state.loja,
            'vendedor': vend,
            'cliente': cli,
            'data': horario_sp.strftime("%d/%m/%Y"),
            'hora': horario_sp.strftime("%H:%M"),
            'atendimento': '1',
            'receita': '',  
            'perda': '1' if tipo == "DESISTÊNCIA" else '',
            'venda': '1' if tipo == "CONVERSÃO" else '',
            'reserva': '-1',  
            'pesquisa': '',
            'exame': '',
        }

        # 📥 Salva no Google Sheets
        try:
            sucesso = gsheets.registrar_atendimento(dados_registro)
        except Exception as e:
            st.error(f"❌ Erro ao salvar: {e}")
            sucesso = False

        if sucesso:
            st.balloons()
            st.success("✅ Registro salvo com sucesso!")
            # Limpa o estado
            chaves_limpar = ['tipo_reserva', 'cliente_reserva', 'vendedor_reserva']
            for key in chaves_limpar:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state.etapa = 'loja' 
            st.rerun()
        else:
            st.error("❌ Falha ao salvar no Google Sheets.")

    # Botão Voltar
    if st.button("↩️ VOLTAR", use_container_width=True, key="btn_voltar_reservas_2"):
        chaves_limpar = ['tipo_reserva', 'cliente_reserva', 'vendedor_reserva']
        for key in chaves_limpar:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state.etapa = 'atendimento'  
        st.rerun()