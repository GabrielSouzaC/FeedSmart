import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sqlite3
import hashlib
import os
import datetime
import time
import uuid
from streamlit_chat import message

# Configuração da página
st.set_page_config(page_title="Sistema de Feedback", layout="wide")

# Inicializar banco de dados
def init_db():
    conn = sqlite3.connect('feedback_app.db')
    c = conn.cursor()
    
    # Criar tabela de usuários se não existir
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        name TEXT,
        email TEXT
    )
    ''')
    
    # Criar tabela de feedback se não existir
    c.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        rating INTEGER,
        comment TEXT,
        timestamp TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Função para hash de senha
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Função para verificar login
def verify_login(username, password):
    conn = sqlite3.connect('feedback_app.db')
    c = conn.cursor()
    
    c.execute("SELECT id, password, name FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    
    if result and result[1] == hash_password(password):
        return {"id": result[0], "name": result[2]}
    return None

# Função para registrar novo usuário
def register_user(username, password, name, email):
    conn = sqlite3.connect('feedback_app.db')
    c = conn.cursor()
    
    try:
        user_id = str(uuid.uuid4())
        c.execute(
            "INSERT INTO users (id, username, password, name, email) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, hash_password(password), name, email)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

# Função para salvar feedback
def save_feedback(user_id, rating, comment):
    conn = sqlite3.connect('feedback_app.db')
    c = conn.cursor()
    
    feedback_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute(
        "INSERT INTO feedback (id, user_id, rating, comment, timestamp) VALUES (?, ?, ?, ?, ?)",
        (feedback_id, user_id, rating, comment, timestamp)
    )
    
    conn.commit()
    conn.close()
    return feedback_id

# Função para obter todos os feedbacks de um usuário
def get_user_feedbacks(user_id):
    conn = sqlite3.connect('feedback_app.db')
    df = pd.read_sql_query("SELECT * FROM feedback WHERE user_id = ? ORDER BY timestamp DESC", 
                          conn, params=(user_id,))
    conn.close()
    return df

# Inicializar o banco de dados
init_db()

# Inicializar estado da sessão
if 'user' not in st.session_state:
    st.session_state.user = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_feedback' not in st.session_state:
    st.session_state.current_feedback = {"stage": 0, "rating": None, "comment": None}

# Função para mudar de página
def change_page(page):
    st.session_state.page = page
    
# Função para fazer logout
def logout():
    st.session_state.user = None
    st.session_state.page = 'login'
    st.session_state.chat_history = []
    st.session_state.current_feedback = {"stage": 0, "rating": None, "comment": None}

# Função para processar a entrada do chatbot
def process_chat_input(user_input):
    feedback = st.session_state.current_feedback
    
    if feedback["stage"] == 0:
        # Iniciar conversa
        st.session_state.chat_history.append({"role": "assistant", "content": "Olá! Gostaria de coletar seu feedback. Em uma escala de 0 a 5, como você avaliaria nossa plataforma?"})
        feedback["stage"] = 1
    elif feedback["stage"] == 1:
        # Processar avaliação
        try:
            rating = int(user_input)
            if 0 <= rating <= 5:
                feedback["rating"] = rating
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({"role": "assistant", "content": f"Obrigado pela avaliação de {rating}/5! Você gostaria de adicionar algum comentário sobre sua experiência?"})
                feedback["stage"] = 2
            else:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({"role": "assistant", "content": "Por favor, forneça uma avaliação entre 0 e 5."})
        except ValueError:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.chat_history.append({"role": "assistant", "content": "Por favor, forneça um número entre 0 e 5 para sua avaliação."})
    elif feedback["stage"] == 2:
        # Processar comentário
        feedback["comment"] = user_input
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Salvar feedback no banco de dados
        save_feedback(st.session_state.user["id"], feedback["rating"], feedback["comment"])
        
        st.session_state.chat_history.append({"role": "assistant", "content": "Obrigado pelo seu feedback! Ele foi registrado com sucesso. Deseja fornecer outro feedback? (sim/não)"})
        feedback["stage"] = 3
    elif feedback["stage"] == 3:
        # Verificar se o usuário quer dar outro feedback
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        if user_input.lower() in ["sim", "s", "yes", "y"]:
            st.session_state.chat_history.append({"role": "assistant", "content": "Ótimo! Em uma escala de 0 a 5, como você avaliaria nossa plataforma?"})
            st.session_state.current_feedback = {"stage": 1, "rating": None, "comment": None}
        else:
            st.session_state.chat_history.append({"role": "assistant", "content": "Obrigado por participar! Se quiser ver seus feedbacks anteriores, acesse a seção de Dashboard."})
            st.session_state.current_feedback = {"stage": 0, "rating": None, "comment": None}

# Página de Login
def login_page():
    st.title("Sistema de Feedback - Login")
    
    tab1, tab2 = st.tabs(["Login", "Registrar"])
    
    with tab1:
        username = st.text_input("Nome de usuário", key="login_username")
        password = st.text_input("Senha", type="password", key="login_password")
        
        if st.button("Entrar"):
            user = verify_login(username, password)
            if user:
                st.session_state.user = user
                st.session_state.page = 'home'
                st.rerun()
            else:
                st.error("Nome de usuário ou senha incorretos")
    
    with tab2:
        new_username = st.text_input("Nome de usuário", key="reg_username")
        new_password = st.text_input("Senha", type="password", key="reg_password")
        confirm_password = st.text_input("Confirmar senha", type="password")
        name = st.text_input("Nome completo")
        email = st.text_input("Email")
        
        if st.button("Registrar"):
            if new_password != confirm_password:
                st.error("As senhas não coincidem")
            elif not (new_username and new_password and name and email):
                st.error("Todos os campos são obrigatórios")
            else:
                if register_user(new_username, new_password, name, email):
                    st.success("Registro concluído com sucesso! Faça login para continuar.")
                else:
                    st.error("Nome de usuário já existe")

# Página inicial
def home_page():
    st.title(f"Bem-vindo, {st.session_state.user['name']}!")
    
    # Barra lateral com navegação
    with st.sidebar:
        st.title("Navegação")
        st.button("Página Inicial", on_click=change_page, args=('home',))
        st.button("Chatbot de Feedback", on_click=change_page, args=('chatbot',))
        st.button("Dashboard", on_click=change_page, args=('dashboard',))
        st.button("Sair", on_click=logout)
    
    st.write("Este é um sistema de coleta de feedback através de um chatbot interativo.")
    st.write("Utilize o menu lateral para navegar entre as diferentes seções do aplicativo.")
    
    st.subheader("Funcionalidades:")
    st.markdown("""
    - **Chatbot de Feedback**: Interaja com nosso chatbot para fornecer avaliações de 0 a 5 e comentários.
    - **Dashboard**: Visualize todos os seus feedbacks anteriores e estatísticas.
    """)

# Página do chatbot
def chatbot_page():
    st.title("Chatbot de Feedback")
    
    # Barra lateral com navegação
    with st.sidebar:
        st.title("Navegação")
        st.button("Página Inicial", on_click=change_page, args=('home',))
        st.button("Chatbot de Feedback", on_click=change_page, args=('chatbot',))
        st.button("Dashboard", on_click=change_page, args=('dashboard',))
        st.button("Sair", on_click=logout)
    
    # Iniciar conversa se for a primeira vez
    if len(st.session_state.chat_history) == 0:
        process_chat_input("")
    
    # Exibir histórico de chat
    chat_container = st.container()
    with chat_container:
        for i, chat in enumerate(st.session_state.chat_history):
            if chat["role"] == "user":
                message(chat["content"], is_user=True, key=f"msg_{i}")
            else:
                message(chat["content"], is_user=False, key=f"msg_{i}")
    
    # Input do usuário
    user_input = st.text_input("Digite sua mensagem:", key="user_input")
    
    if st.button("Enviar") and user_input:
        process_chat_input(user_input)
        st.rerun()

# Página de dashboard
def dashboard_page():
    st.title("Dashboard de Feedback")
    
    # Barra lateral com navegação
    with st.sidebar:
        st.title("Navegação")
        st.button("Página Inicial", on_click=change_page, args=('home',))
        st.button("Chatbot de Feedback", on_click=change_page, args=('chatbot',))
        st.button("Dashboard", on_click=change_page, args=('dashboard',))
        st.button("Sair", on_click=logout)
    
    # Obter feedbacks do usuário
    feedbacks = get_user_feedbacks(st.session_state.user["id"])
    
    if len(feedbacks) == 0:
        st.info("Você ainda não forneceu nenhum feedback. Use o chatbot para começar!")
    else:
        # Mostrar estatísticas
        st.subheader("Estatísticas de Feedback")
        
        col1, col2 = st.columns(2)
        
        with col1:
            avg_rating = feedbacks['rating'].mean()
            st.metric("Avaliação Média", f"{avg_rating:.1f}/5")
            
            # Gráfico de distribuição de avaliações
            fig, ax = plt.subplots(figsize=(10, 6))
            feedbacks['rating'].value_counts().sort_index().plot(kind='bar', ax=ax)
            ax.set_title('Distribuição de Avaliações')
            ax.set_xlabel('Avaliação')
            ax.set_ylabel('Contagem')
            ax.set_xticks(range(6))
            ax.set_xticklabels(['0', '1', '2', '3', '4', '5'])
            st.pyplot(fig)
        
        with col2:
            total_feedbacks = len(feedbacks)
            st.metric("Total de Feedbacks", total_feedbacks)
            
            # Gráfico de avaliações ao longo do tempo
            feedbacks['timestamp'] = pd.to_datetime(feedbacks['timestamp'])
            feedbacks.set_index('timestamp', inplace=True)
            
            # Resample por dia e calcular média
            daily_avg = feedbacks['rating'].resample('D').mean().fillna(0)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            daily_avg.plot(ax=ax)
            ax.set_title('Avaliação Média por Dia')
            ax.set_xlabel('Data')
            ax.set_ylabel('Avaliação Média')
            ax.set_ylim(0, 5)
            st.pyplot(fig)
        
        # Tabela de feedbacks
        st.subheader("Seus Feedbacks")
        
        # Preparar dados para exibição
        display_df = feedbacks[['timestamp', 'rating', 'comment']].copy()
        display_df.columns = ['Data/Hora', 'Avaliação', 'Comentário']
        display_df['Data/Hora'] = pd.to_datetime(display_df['Data/Hora']).dt.strftime('%d/%m/%Y %H:%M')
        
        st.dataframe(display_df, use_container_width=True)

# Renderizar a página apropriada
if st.session_state.user is None:
    login_page()
else:
    if st.session_state.page == 'home':
        home_page()
    elif st.session_state.page == 'chatbot':
        chatbot_page()
    elif st.session_state.page == 'dashboard':
        dashboard_page()