import streamlit as st

def tl_atendimento_principal():
    st.title("💼 TELA DE ATENDIMENTO")
    st.info(f"**Loja:** {st.session_state.get('loja', 'Não selecionada')}")
    st.info(f"**Usuário:** {st.session_state.get('nome_atendente', 'Desconhecido')}")
    st.markdown("---")  # Linha divisória mais elegante

    # Lista de botões: (Texto, chave)
    botoes = [
        ("💊 Atendimento com Receita", "receita"),
        ("📌 Reservas Acumuladas", "reserva"),
        ("🔄 Retorno sem Reserva", "sem_receita"),
        ("🔍 Atendimento de Terceiros", "pesquisa"),
        ("🔧 Ajuste", "ajuste"),
        ("📦 Entrega de óculos", "entrega"),
        ("🛠️ Garantia", "garantia"),
        ("📅 Exame de Vista", "exame"),
    ]

    # Exibe os botões em pares (2 por linha)
    for i in range(0, len(botoes), 2):
        col1, col2 = st.columns(2)

        # Primeiro botão (sempre existe)
        texto1, chave1 = botoes[i]
        with col1:
            if st.button(texto1, use_container_width=True, key=f"btn_{chave1}"):
                st.session_state.subtela = chave1
                st.session_state.etapa = 'subtela'
                st.rerun()

        # Segundo botão (só se existir)
        if i + 1 < len(botoes):
            texto2, chave2 = botoes[i + 1]
            with col2:
                if st.button(texto2, use_container_width=True, key=f"btn_{chave2}"):
                    st.session_state.subtela = chave2
                    st.session_state.etapa = 'subtela'
                    st.rerun()

    st.link_button("🖨️ Comanda de Venda", "https://diniz-bamarcone.optfacil.com.br/legacy/login", use_container_width=True)
    st.markdown("---")

    # Botão de voltar
    if st.button("🚪 VOLTAR", use_container_width=True, type="secondary"):
        # Limpa os estados relevantes
        st.session_state.etapa = 'loja'
        st.session_state.loja = ''
        st.session_state.subtela = ''
        st.rerun()