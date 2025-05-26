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

# ==================== ESTRUTURAS DE DADOS INTEGRADAS ====================

class FeedbackQueue:
    """
    Implementação de uma fila para gerenciar solicitações de feedback.
    
    Esta estrutura de dados segue o princípio FIFO (First In, First Out),
    onde o primeiro feedback adicionado será o primeiro a ser processado.
    """
    
    def __init__(self):
        """Inicializa uma fila vazia."""
        self.items = []
    
    def is_empty(self):
        """Verifica se a fila está vazia."""
        return len(self.items) == 0
    
    def enqueue(self, item):
        """Adiciona um item ao final da fila."""
        self.items.append(item)
    
    def dequeue(self):
        """Remove e retorna o item do início da fila."""
        if self.is_empty():
            return None
        return self.items.pop(0)
    
    def peek(self):
        """Retorna o item do início da fila sem removê-lo."""
        if self.is_empty():
            return None
        return self.items[0]
    
    def size(self):
        """Retorna o tamanho da fila."""
        return len(self.items)
    
    def clear(self):
        """Limpa a fila."""
        self.items = []
    
    def get_all(self):
        """Retorna todos os itens da fila sem removê-los."""
        return self.items.copy()
    
    def process_next(self):
        """
        Processa o próximo feedback na fila.
        Este método pode ser expandido para realizar ações específicas com o feedback.
        """
        next_feedback = self.dequeue()
        if next_feedback:
            return next_feedback
        return None

# ==================== ALGORITMOS DE ORDENAÇÃO INTEGRADOS ====================

def merge_sort_by_rating(arr):
    """
    Implementação do algoritmo Merge Sort para ordenar índices com base nos valores de avaliação.
    Retorna uma lista de índices ordenados do maior para o menor valor.
    
    Args:
        arr: Lista de valores de avaliação
        
    Returns:
        Lista de índices ordenados
    """
    # Criar lista de tuplas (valor, índice)
    indexed_arr = [(arr[i], i) for i in range(len(arr))]
    
    # Função interna para dividir e conquistar
    def merge_sort(arr):
        if len(arr) <= 1:
            return arr
        
        # Dividir o array
        mid = len(arr) // 2
        left = merge_sort(arr[:mid])
        right = merge_sort(arr[mid:])
        
        # Conquistar (mesclar)
        return merge(left, right)
    
    # Função para mesclar duas listas ordenadas
    def merge(left, right):
        result = []
        i = j = 0
        
        # Mesclar ordenando do maior para o menor (ordem decrescente)
        while i < len(left) and j < len(right):
            # Comparar os valores (primeiro elemento da tupla)
            if left[i][0] >= right[j][0]:
                result.append(left[i])
                i += 1
            else:
                result.append(right[j])
                j += 1
        
        # Adicionar elementos restantes
        result.extend(left[i:])
        result.extend(right[j:])
        
        return result
    
    # Executar o merge sort
    sorted_arr = merge_sort(indexed_arr)
    
    # Extrair apenas os índices da lista ordenada
    return [item[1] for item in sorted_arr]

# ==================== BANCO DE DADOS ====================

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
        priority INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Verificar se a coluna priority existe e adicioná-la se necessário
    try:
        c.execute("SELECT priority FROM feedback LIMIT 1")
    except sqlite3.OperationalError:
        # Coluna priority não existe, vamos adicioná-la
        c.execute("ALTER TABLE feedback ADD COLUMN priority INTEGER DEFAULT 0")
        print("Coluna 'priority' adicionada à tabela feedback")
    
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

# Função para salvar feedback (ATUALIZADA com fila)
def save_feedback(user_id, rating, comment):
    conn = sqlite3.connect('feedback_app.db')
    c = conn.cursor()
    
    feedback_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Determinar prioridade baseada na avaliação (avaliações baixas têm prioridade maior)
    priority = 6 - int(rating)  # Avaliação 1 = prioridade 5, Avaliação 5 = prioridade 1
    
    c.execute(
        "INSERT INTO feedback (id, user_id, rating, comment, timestamp, priority) VALUES (?, ?, ?, ?, ?, ?)",
        (feedback_id, user_id, rating, comment, timestamp, priority)
    )
    
    # Adicionar à fila de processamento
    if 'feedback_queue' not in st.session_state:
        st.session_state.feedback_queue = FeedbackQueue()
    
    feedback_item = {
        'id': feedback_id,
        'user_id': user_id,
        'rating': rating,
        'comment': comment,
        'timestamp': timestamp,
        'priority': priority
    }
    st.session_state.feedback_queue.enqueue(feedback_item)
    
    conn.commit()
    conn.close()
    return feedback_id

# Função para obter todos os feedbacks de um usuário (ATUALIZADA com ordenação)
def get_user_feedbacks(user_id, sort_method='timestamp'):
    conn = sqlite3.connect('feedback_app.db')
    df = pd.read_sql_query("SELECT * FROM feedback WHERE user_id = ? ORDER BY timestamp DESC", 
                          conn, params=(user_id,))
    conn.close()
    
    if len(df) > 0 and sort_method == 'rating':
        # Usar o algoritmo de merge sort customizado
        ratings = df['rating'].tolist()
        sorted_indices = merge_sort_by_rating(ratings)
        df = df.iloc[sorted_indices].reset_index(drop=True)
    
    return df

# ==================== ESTADO DA SESSÃO ====================

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
    st.session_state.current_feedback = {"stage": 0, "product": None, "product_rating": None, "delivery_rating": None, "comment": None}
if 'feedback_queue' not in st.session_state:
    st.session_state.feedback_queue = FeedbackQueue()

# ==================== FUNÇÕES DE NAVEGAÇÃO ====================

# Função para mudar de página
def change_page(page):
    st.session_state.page = page
    
# Função para fazer logout
def logout():
    st.session_state.user = None
    st.session_state.page = 'login'
    st.session_state.chat_history = []
    st.session_state.current_feedback = {"stage": 0, "product": None, "product_rating": None, "delivery_rating": None, "comment": None}

# ==================== PROCESSAMENTO DO CHATBOT ====================

# Função para processar a entrada do chatbot
def process_chat_input(user_input):
    feedback = st.session_state.current_feedback
    
    if feedback["stage"] == 0:
        # Iniciar conversa com boas-vindas
        st.session_state.chat_history.append({"role": "assistant", "content": "Olá! Bem-vindo ao nosso sistema de feedback. Estamos felizes em tê-lo aqui!"})
        st.session_state.chat_history.append({"role": "assistant", "content": "Qual produto você adquiriu recentemente?"})
        feedback["stage"] = 1
    elif feedback["stage"] == 1:
        # Processar seleção de produto
        feedback["product"] = user_input
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        st.session_state.chat_history.append({"role": "assistant", "content": f"Ótimo! Você adquiriu {user_input}. Em uma escala de 0 a 5, como você avaliaria a qualidade deste produto?"})
        feedback["stage"] = 2
    elif feedback["stage"] == 2:
        # Processar avaliação do produto
        try:
            rating = int(user_input)
            if 0 <= rating <= 5:
                feedback["product_rating"] = rating
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({"role": "assistant", "content": f"Obrigado pela avaliação de {rating}/5 para o produto! Agora, em uma escala de 0 a 5, como você avaliaria o prazo de entrega?"})
                feedback["stage"] = 3
            else:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({"role": "assistant", "content": "Por favor, forneça uma avaliação entre 0 e 5."})
        except ValueError:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.chat_history.append({"role": "assistant", "content": "Por favor, forneça um número entre 0 e 5 para sua avaliação."})
    elif feedback["stage"] == 3:
        # Processar avaliação do prazo de entrega
        try:
            rating = int(user_input)
            if 0 <= rating <= 5:
                feedback["delivery_rating"] = rating
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({"role": "assistant", "content": f"Obrigado pela avaliação de {rating}/5 para o prazo de entrega! Você gostaria de adicionar algum comentário sobre sua experiência?"})
                feedback["stage"] = 4
            else:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({"role": "assistant", "content": "Por favor, forneça uma avaliação entre 0 e 5."})
        except ValueError:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.chat_history.append({"role": "assistant", "content": "Por favor, forneça um número entre 0 e 5 para sua avaliação."})
    elif feedback["stage"] == 4:
        # Processar comentário
        feedback["comment"] = user_input
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Calcular média das avaliações
        avg_rating = (feedback["product_rating"] + feedback["delivery_rating"]) / 2
        
        # Salvar feedback no banco de dados (agora com fila integrada)
        save_feedback(st.session_state.user["id"], avg_rating, f"Produto: {feedback['product']} | Avaliação do produto: {feedback['product_rating']}/5 | Avaliação da entrega: {feedback['delivery_rating']}/5 | Comentário: {feedback['comment']}")
        
        st.session_state.chat_history.append({"role": "assistant", "content": "Obrigado pelo seu feedback! Ele foi registrado com sucesso e adicionado à nossa fila de processamento. Deseja fornecer outro feedback? (sim/não)"})
        feedback["stage"] = 5
    elif feedback["stage"] == 5:
        # Verificar se o usuário quer dar outro feedback
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        if user_input.lower() in ["sim", "s", "yes", "y"]:
            st.session_state.chat_history.append({"role": "assistant", "content": "Ótimo! Qual produto você adquiriu recentemente?"})
            st.session_state.current_feedback = {"stage": 1, "product": None, "product_rating": None, "delivery_rating": None, "comment": None}
        else:
            st.session_state.chat_history.append({"role": "assistant", "content": "Obrigado por participar! Se quiser ver seus feedbacks anteriores, acesse a seção de Dashboard."})
            st.session_state.current_feedback = {"stage": 0, "product": None, "product_rating": None, "delivery_rating": None, "comment": None}

# ==================== PÁGINAS ====================

# Página de Login
def login_page():
    st.title("FeedSmart - Login")
    
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
        st.button("Fila de Processamento", on_click=change_page, args=('queue',))
        st.button("Sair", on_click=logout)
    
    st.write("Este é um sistema de coleta de feedback através de um chatbot interativo.")
    st.write("Utilize o menu lateral para navegar entre as diferentes seções do aplicativo.")
    
    st.subheader("Funcionalidades:")
    st.markdown("""
    - **Chatbot de Feedback**: Interaja com nosso chatbot para fornecer avaliações de 0 a 5 e comentários.
    - **Dashboard**: Visualize todos os seus feedbacks anteriores e estatísticas com ordenação inteligente.
    - **Fila de Processamento**: Veja os feedbacks na fila de processamento organizados por prioridade.
    """)
    
    # Mostrar estatísticas rápidas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        queue_size = st.session_state.feedback_queue.size()
        st.metric("Feedbacks na Fila", queue_size)
    
    with col2:
        feedbacks = get_user_feedbacks(st.session_state.user["id"])
        total_feedbacks = len(feedbacks)
        st.metric("Total de Feedbacks", total_feedbacks)
    
    with col3:
        if total_feedbacks > 0:
            avg_rating = feedbacks['rating'].mean()
            st.metric("Avaliação Média", f"{avg_rating:.1f}/5")
        else:
            st.metric("Avaliação Média", "N/A")

def clear_chat_history():
    """Limpa o histórico do chat e reinicia a conversa"""
    st.session_state.chat_history = []
    st.session_state.current_feedback = {"stage": 0, "product": None, "product_rating": None, "delivery_rating": None, "comment": None}

# Página do chatbot
def chatbot_page():
    st.title("Chatbot de Feedback")
    
    # Barra lateral com navegação
    with st.sidebar:
        st.title("Navegação")
        st.button("Página Inicial", on_click=change_page, args=('home',))
        st.button("Chatbot de Feedback", on_click=change_page, args=('chatbot',))
        st.button("Dashboard", on_click=change_page, args=('dashboard',))
        st.button("Fila de Processamento", on_click=change_page, args=('queue',))
        st.button("Sair", on_click=logout)
        
        st.divider()
        if st.button("🗑️ Limpar Histórico", help="Limpa todo o histórico da conversa"):
            clear_chat_history()
            st.success("Histórico limpo com sucesso!")
            st.rerun()
    
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
    if st.session_state.current_feedback["stage"] == 1:
        # Mostrar seleção de produto
        product_options = ["Camiseta", "Shorts", "Calça", "Tênis"]
        user_input = st.selectbox("Selecione o produto:", product_options)
        submit_button = st.button("Enviar")
        
        if submit_button:
            process_chat_input(user_input)
            st.rerun()
    else:
        # Input de texto normal
        user_input = st.text_input("Digite sua mensagem:", key="user_input")
        
        if st.button("Enviar") and user_input:
            process_chat_input(user_input)
            st.rerun()

# Página de dashboard (ATUALIZADA)
def dashboard_page():
    st.title("Dashboard de Feedback")
    
    # Barra lateral com navegação
    with st.sidebar:
        st.title("Navegação")
        st.button("Página Inicial", on_click=change_page, args=('home',))
        st.button("Chatbot de Feedback", on_click=change_page, args=('chatbot',))
        st.button("Dashboard", on_click=change_page, args=('dashboard',))
        st.button("Fila de Processamento", on_click=change_page, args=('queue',))
        st.button("Sair", on_click=logout)
    
    # Opções de ordenação
    st.subheader("Opções de Visualização")
    sort_option = st.selectbox(
        "Ordenar feedbacks por:",
        ["Data (mais recente)", "Avaliação (maior para menor)"],
        key="sort_option"
    )
    
    sort_method = 'rating' if 'Avaliação' in sort_option else 'timestamp'
    
    # Obter feedbacks do usuário
    feedbacks = get_user_feedbacks(st.session_state.user["id"], sort_method)
    
    if len(feedbacks) == 0:
        st.info("Você ainda não forneceu nenhum feedback. Use o chatbot para começar!")
    else:
        # Mostrar estatísticas
        st.subheader("Estatísticas de Feedback")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_rating = feedbacks['rating'].mean()
            st.metric("Avaliação Média", f"{avg_rating:.1f}/5")
        
        with col2:
            max_rating = feedbacks['rating'].max()
            st.metric("Maior Avaliação", f"{max_rating:.1f}/5")
        
        with col3:
            min_rating = feedbacks['rating'].min()
            st.metric("Menor Avaliação", f"{min_rating:.1f}/5")
        
        # Gráfico de média de avaliações ao longo do tempo
        if len(feedbacks) > 1:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Converter timestamp para datetime e ordenar por data
            feedbacks_for_chart = feedbacks.copy()
            feedbacks_for_chart['timestamp'] = pd.to_datetime(feedbacks_for_chart['timestamp'])
            feedbacks_for_chart = feedbacks_for_chart.sort_values('timestamp')
            
            # Calcular média móvel das avaliações
            feedbacks_for_chart['avg_rating_cumulative'] = feedbacks_for_chart['rating'].expanding().mean()
            
            # Plotar linha da média cumulativa
            ax.plot(feedbacks_for_chart['timestamp'], feedbacks_for_chart['avg_rating_cumulative'], 
                    marker='o', linewidth=2, markersize=6, color='#1f77b4')
            
            # Adicionar linha horizontal da média geral
            ax.axhline(y=avg_rating, color='red', linestyle='--', alpha=0.7, 
                       label=f'Média Geral: {avg_rating:.1f}')
            
            # Configurações do gráfico
            ax.set_title('Evolução da Média de Avaliações ao Longo do Tempo', fontsize=14, fontweight='bold')
            ax.set_xlabel('Data', fontsize=12)
            ax.set_ylabel('Média de Avaliação', fontsize=12)
            ax.set_ylim(0, 5.5)
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Formatar eixo x para mostrar datas de forma mais legível
            import matplotlib.dates as mdates
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(feedbacks)//5)))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            st.pyplot(fig)
            
        else:
            # Para apenas um feedback, mostrar um gráfico de gauge simples
            fig, ax = plt.subplots(figsize=(8, 6))
            
            # Criar um gráfico de barras horizontal simples para mostrar a média
            categories = ['Sua Avaliação Média']
            values = [avg_rating]
            colors = ['#1f77b4']
            
            bars = ax.barh(categories, values, color=colors, alpha=0.7)
            ax.set_xlim(0, 5)
            ax.set_xlabel('Avaliação (0-5)', fontsize=12)
            ax.set_title('Sua Média de Avaliações', fontsize=14, fontweight='bold')
            
            # Adicionar o valor na barra
            for bar, value in zip(bars, values):
                ax.text(value + 0.1, bar.get_y() + bar.get_height()/2, 
                        f'{value:.1f}', va='center', fontsize=12, fontweight='bold')
            
            ax.grid(True, alpha=0.3, axis='x')
            plt.tight_layout()
            st.pyplot(fig)
        
        # Tabela de feedbacks
        st.subheader(f"Seus Feedbacks (Ordenados por {sort_option})")
        
        # Preparar dados para exibição
        display_df = feedbacks[['timestamp', 'rating', 'comment']].copy()
        display_df.columns = ['Data/Hora', 'Avaliação', 'Comentário']
        display_df['Data/Hora'] = pd.to_datetime(display_df['Data/Hora']).dt.strftime('%d/%m/%Y %H:%M')
        
        st.dataframe(display_df, use_container_width=True)

# Nova página da fila de processamento
def queue_page():
    st.title("Fila de Processamento de Feedback")
    
    # Barra lateral com navegação
    with st.sidebar:
        st.title("Navegação")
        st.button("Página Inicial", on_click=change_page, args=('home',))
        st.button("Chatbot de Feedback", on_click=change_page, args=('chatbot',))
        st.button("Dashboard", on_click=change_page, args=('dashboard',))
        st.button("Fila de Processamento", on_click=change_page, args=('queue',))
        st.button("Sair", on_click=logout)
    
    st.write("Esta página mostra os feedbacks na fila de processamento, organizados por prioridade.")
    
    # Informações da fila
    queue_size = st.session_state.feedback_queue.size()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Itens na Fila", queue_size)
    
    with col2:
        if not st.session_state.feedback_queue.is_empty():
            next_item = st.session_state.feedback_queue.peek()
            st.metric("Próximo na Fila", f"Avaliação {next_item['rating']}/5")
    
    # Mostrar itens da fila
    if queue_size > 0:
        st.subheader("Itens na Fila de Processamento")
        
        queue_items = st.session_state.feedback_queue.get_all()
        
        # Criar DataFrame para exibição
        queue_df = pd.DataFrame(queue_items)
        queue_df['timestamp'] = pd.to_datetime(queue_df['timestamp']).dt.strftime('%d/%m/%Y %H:%M')
        
        # Ordenar por prioridade (maior prioridade primeiro)
        queue_df = queue_df.sort_values('priority', ascending=False)
        
        # Exibir tabela
        display_columns = ['timestamp', 'rating', 'priority', 'comment']
        display_df = queue_df[display_columns].copy()
        display_df.columns = ['Data/Hora', 'Avaliação', 'Prioridade', 'Comentário']
        
        st.dataframe(display_df, use_container_width=True)
        
        # Botões de ação
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Processar Próximo"):
                processed = st.session_state.feedback_queue.process_next()
                if processed:
                    st.success(f"Feedback processado: Avaliação {processed['rating']}/5")
                    st.rerun()
                else:
                    st.warning("Nenhum item na fila para processar")
        
        with col2:
            if st.button("Limpar Fila"):
                st.session_state.feedback_queue.clear()
                st.success("Fila limpa com sucesso!")
                st.rerun()
        
        with col3:
            st.write(f"Total de itens: {queue_size}")
    
    else:
        st.info("A fila de processamento está vazia. Adicione feedbacks através do chatbot!")

# ==================== RENDERIZAÇÃO PRINCIPAL ====================

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
    elif st.session_state.page == 'queue':
        queue_page()
