import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo
from google_planilha import GooglePlanilha

def tl_entrega():
    st.subheader("📦 ENTREGA DE ÓCULOS")
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

    # Carregar vendedores
    vendedores_data = gsheets.get_vendedores_por_loja()
    vendedores = [v['VENDEDOR'] for v in vendedores_data]

    if not vendedores:
        st.warning("⚠️ Nenhum vendedor encontrado para esta loja.")
        if st.button("↩️ Voltar", key="btn_voltar_entrega"):
            st.session_state.etapa = 'atendimento'
            st.rerun()
        return

    # Seleção de vendedor (opcional)
    vendedor = st.selectbox(
        "Vendedor (opcional)",
        [""] + vendedores,
        index=0,
        placeholder="Selecione o vendedor (opcional)",
        key="vend_entrega"
    )

    # Nome do cliente
    cliente = st.text_input("Nome do Cliente", key="cliente_entrega_input")
    cliente = cliente.strip().upper()

    # === REGISTRO DO TIPO: ENTREGA ===
    if st.button("✅ CONFIRMAR", type="primary", key="btn_confirmar_entrega"):
        if not cliente:
            st.error("⚠️ Preencha o nome do cliente!")
        else:
            # Armazena no session_state
            st.session_state.tipo_registro = "ENTREGA"
            st.session_state.cliente_entrega = cliente
            st.session_state.vendedor_entrega = vendedor if vendedor else ""
            st.rerun()

    # Mostra a confirmação se já foi feita
    if 'tipo_registro' in st.session_state and st.session_state.tipo_registro == "ENTREGA":
        cliente_conf = st.session_state.cliente_entrega
        vendedor_conf = st.session_state.vendedor_entrega
        st.markdown("---")
        st.success(f"✅ **CONFIRMADO**: {cliente_conf} | **Tipo:** ENTREGA | Vendedor: {vendedor_conf or 'Nenhum'}")

        # Confirmação final e registro
        if st.button("💾 REGISTRAR ENTREGA", type="primary", use_container_width=True, key="btn_salvar_entrega"):
            # ✅ Usa horário de São Paulo
            horario_sp = datetime.now(ZoneInfo("America/Sao_Paulo"))

            dados = {
                'loja': st.session_state.loja,
                'atendente': st.session_state.nome_atendente,
                'vendedor': vendedor_conf,
                'cliente': cliente_conf,
                'data': horario_sp.strftime("%d/%m/%Y"),
                'hora': horario_sp.strftime("%H:%M"),
                'atendimento': '1',
                'receita': '',
                'venda': '',
                'perda': '',
                'reserva': '',
                'pesquisa': '',
                'gar_lente': '',
                'gar_armacao': '',
                'ajuste': '',
                'entrega': '1',
                'consulta': '',
            }

            if gsheets.registrar_atendimento(dados):
                st.balloons()
                st.success("✅ Pesquisa registrada com sucesso!")
                # Limpa o estado
                del st.session_state.tipo_registro
                del st.session_state.cliente_pesquisa
                del st.session_state.vendedor_pesquisa
                st.session_state.etapa = 'loja'  
                st.rerun()
            else:
                st.error("❌ Falha ao salvar na planilha.")

    # Botão Voltar
    if st.button("↩️ VOLTAR", key="btn_voltar_entrega_2"):
        if 'tipo_registro' in st.session_state:
            del st.session_state.tipo_registro
            del st.session_state.cliente_entrega
            del st.session_state.vendedor_entrega
        st.session_state.etapa = 'atendimento'
        st.rerun()