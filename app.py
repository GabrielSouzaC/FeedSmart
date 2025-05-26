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
import re
from streamlit_chat import message

# Configuração da página
st.set_page_config(page_title="FeedSmart - Sistema de Feedback", layout="wide", page_icon="🤖")

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
        Processa o próximo feedback na fila baseado na prioridade.
        Remove e retorna o item com maior prioridade.
        """
        if self.is_empty():
            return None
        
        # Encontrar item com maior prioridade (maior número = maior prioridade)
        max_priority_index = 0
        for i in range(1, len(self.items)):
            if self.items[i]['priority'] > self.items[max_priority_index]['priority']:
                max_priority_index = i
        
        # Remover e retornar o item de maior prioridade
        return self.items.pop(max_priority_index)
    
    def get_sorted_by_priority(self):
        """Retorna itens ordenados por prioridade (maior prioridade primeiro)."""
        return sorted(self.items, key=lambda x: x['priority'], reverse=True)

# ==================== ALGORITMOS DE ORDENAÇÃO INTEGRADOS ====================

def merge_sort_by_rating(arr):
    """
    Implementação do algoritmo Merge Sort para ordenar índices com base nos valores de avaliação.
    Retorna uma lista de índices ordenados do maior para o menor valor.
    
    Complexidade: O(n log n)
    Tipo: Divisão e conquista
    Estável: Sim
    
    Args:
        arr: Lista de valores de avaliação
        
    Returns:
        Lista de índices ordenados (maior para menor)
    """
    # Criar lista de tuplas (valor, índice)
    indexed_arr = [(arr[i], i) for i in range(len(arr))]
    
    def merge_sort(arr):
        """Função recursiva principal do merge sort."""
        if len(arr) <= 1:
            return arr
        
        # Dividir o array
        mid = len(arr) // 2
        left = merge_sort(arr[:mid])
        right = merge_sort(arr[mid:])
        
        # Conquistar (mesclar)
        return merge(left, right)
    
    def merge(left, right):
        """Função para mesclar duas listas ordenadas."""
        result = []
        i = j = 0
        
        # Mesclar ordenando do maior para o menor (ordem decrescente)
        while i < len(left) and j < len(right):
            if left[i][0] >= right[j][0]:  # Comparar valores
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

def init_db():
    """Inicializa o banco de dados e cria as tabelas necessárias."""
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
        rating REAL,
        comment TEXT,
        timestamp TEXT,
        priority INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Sistema de migração: Verificar se a coluna priority existe
    try:
        c.execute("SELECT priority FROM feedback LIMIT 1")
    except sqlite3.OperationalError:
        # Coluna priority não existe, vamos adicioná-la
        c.execute("ALTER TABLE feedback ADD COLUMN priority INTEGER DEFAULT 0")
        print("✅ Migração: Coluna 'priority' adicionada à tabela feedback")
    
    # Criar índices para melhor performance
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback(timestamp)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_feedback_priority ON feedback(priority)")
    except sqlite3.Error as e:
        print(f"Aviso: Erro ao criar índices: {e}")
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Criptografa uma senha usando SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    """
    Verifica as credenciais de login do usuário.
    
    Args:
        username (str): Nome de usuário
        password (str): Senha em texto plano
        
    Returns:
        dict or None: Dados do usuário se válido, None se inválido
    """
    conn = sqlite3.connect('feedback_app.db')
    c = conn.cursor()
    
    c.execute("SELECT id, password, name FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    
    if result and result[1] == hash_password(password):
        return {"id": result[0], "name": result[2], "username": username}
    return None

def register_user(username, password, name, email):
    """
    Registra um novo usuário no sistema com validação completa.
    
    Args:
        username (str): Nome de usuário único
        password (str): Senha em texto plano
        name (str): Nome completo
        email (str): Email do usuário
        
    Returns:
        tuple: (success, message)
    """
    # Validação de email usando regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return False, "Email inválido. Use o formato: exemplo@dominio.com"
    
    # Validações adicionais
    if not all([username, password, name, email]):
        return False, "Todos os campos são obrigatórios"
    
    if len(password) < 6:
        return False, "A senha deve ter pelo menos 6 caracteres"
    
    if len(username) < 3:
        return False, "O nome de usuário deve ter pelo menos 3 caracteres"
    
    if len(name) < 2:
        return False, "O nome deve ter pelo menos 2 caracteres"
    
    # Conectar ao banco de dados
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
        return True, "Usuário registrado com sucesso!"
        
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Nome de usuário já existe. Escolha outro."
    except Exception as e:
        conn.close()
        return False, f"Erro inesperado: {str(e)}"

def save_feedback(user_id, rating, comment):
    """
    Salva um feedback no banco de dados e adiciona na fila de processamento.
    
    Args:
        user_id (str): ID do usuário
        rating (float): Avaliação média
        comment (str): Comentário do feedback
        
    Returns:
        str: ID do feedback criado
    """
    conn = sqlite3.connect('feedback_app.db')
    c = conn.cursor()
    
    feedback_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calcular prioridade baseada na avaliação (avaliações baixas = prioridade alta)
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

def get_user_feedbacks(user_id, sort_method='timestamp'):
    """
    Obtém todos os feedbacks de um usuário com opção de ordenação.
    
    Args:
        user_id (str): ID do usuário
        sort_method (str): 'timestamp' ou 'rating'
        
    Returns:
        pandas.DataFrame: Feedbacks do usuário
    """
    conn = sqlite3.connect('feedback_app.db')
    df = pd.read_sql_query(
        "SELECT * FROM feedback WHERE user_id = ? ORDER BY timestamp DESC", 
        conn, params=(user_id,)
    )
    conn.close()
    
    # Aplicar ordenação por avaliação usando Merge Sort se solicitado
    if len(df) > 0 and sort_method == 'rating':
        ratings = df['rating'].tolist()
        sorted_indices = merge_sort_by_rating(ratings)
        df = df.iloc[sorted_indices].reset_index(drop=True)
    
    return df

# ==================== CONFIGURAÇÕES E CONSTANTES ====================

# Produtos disponíveis
PRODUCTS = ["Camiseta", "Shorts", "Calça", "Tênis"]

# Mapeamento de prioridades
PRIORITY_LABELS = {
    5: "🔴 CRÍTICA",
    4: "🟠 ALTA", 
    3: "🟡 MÉDIA",
    2: "🔵 BAIXA",
    1: "🟢 MUITO BAIXA"
}

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
    st.session_state.current_feedback = {
        "stage": 0, 
        "product": None, 
        "product_rating": None, 
        "delivery_rating": None, 
        "comment": None
    }
if 'feedback_queue' not in st.session_state:
    st.session_state.feedback_queue = FeedbackQueue()

# ==================== FUNÇÕES DE NAVEGAÇÃO ====================

def change_page(page):
    """Muda para uma página específica."""
    st.session_state.page = page
    st.rerun()
    
def logout():
    """Realiza logout do usuário limpando a sessão."""
    st.session_state.user = None
    st.session_state.page = 'login'
    st.session_state.chat_history = []
    st.session_state.current_feedback = {
        "stage": 0, 
        "product": None, 
        "product_rating": None, 
        "delivery_rating": None, 
        "comment": None
    }
    st.rerun()

def clear_chat_history():
    """Limpa o histórico do chat e reinicia a conversa."""
    st.session_state.chat_history = []
    st.session_state.current_feedback = {
        "stage": 0, 
        "product": None, 
        "product_rating": None, 
        "delivery_rating": None, 
        "comment": None
    }

# ==================== PROCESSAMENTO DO CHATBOT ====================

def process_chat_input(user_input):
    """
    Processa a entrada do usuário no chatbot baseado no estágio atual.
    
    Args:
        user_input (str): Entrada do usuário
    """
    feedback = st.session_state.current_feedback
    
    if feedback["stage"] == 0:
        # Iniciar conversa com boas-vindas
        welcome_msg = f"Olá, {st.session_state.user['name']}! 👋\n\nSou o assistente de feedback da nossa loja. Vou te ajudar a avaliar sua experiência de compra.\n\nQual produto você gostaria de avaliar?"
        st.session_state.chat_history.append({"role": "assistant", "content": welcome_msg})
        feedback["stage"] = 1
        
    elif feedback["stage"] == 1:
        # Processar seleção de produto
        if user_input in PRODUCTS:
            feedback["product"] = user_input
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": f"Ótimo! Você escolheu: {user_input}\n\nEm uma escala de 0 a 5, como você avalia a qualidade deste produto?\n(0 = Muito ruim, 5 = Excelente)"
            })
            feedback["stage"] = 2
        else:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": "Por favor, selecione um dos produtos disponíveis na lista."
            })
            
    elif feedback["stage"] == 2:
        # Processar avaliação do produto
        try:
            rating = int(user_input)
            if 0 <= rating <= 5:
                feedback["product_rating"] = rating
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({
                    "role": "assistant", 
                    "content": f"Obrigado pela avaliação de {rating}/5 para o produto!\n\nAgora, em uma escala de 0 a 5, como você avalia o prazo de entrega?\n(0 = Muito ruim, 5 = Excelente)"
                })
                feedback["stage"] = 3
            else:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({
                    "role": "assistant", 
                    "content": "Por favor, forneça uma avaliação entre 0 e 5."
                })
        except ValueError:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": "Por favor, forneça um número entre 0 e 5 para sua avaliação."
            })
            
    elif feedback["stage"] == 3:
        # Processar avaliação do prazo de entrega
        try:
            rating = int(user_input)
            if 0 <= rating <= 5:
                feedback["delivery_rating"] = rating
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({
                    "role": "assistant", 
                    "content": f"Perfeito! Nota {rating}/5 para a entrega.\n\nPara finalizar, gostaria de deixar algum comentário adicional sobre sua experiência?"
                })
                feedback["stage"] = 4
            else:
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({
                    "role": "assistant", 
                    "content": "Por favor, forneça uma avaliação entre 0 e 5."
                })
        except ValueError:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": "Por favor, forneça um número entre 0 e 5 para sua avaliação."
            })
            
    elif feedback["stage"] == 4:
        # Processar comentário
        feedback["comment"] = user_input if user_input else "Sem comentários adicionais"
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        # Calcular média das avaliações
        avg_rating = (feedback["product_rating"] + feedback["delivery_rating"]) / 2
        
        # Criar comentário estruturado
        structured_comment = f"Produto: {feedback['product']} | Avaliação do produto: {feedback['product_rating']}/5 | Avaliação da entrega: {feedback['delivery_rating']}/5 | Comentário: {feedback['comment']}"
        
        # Salvar feedback no banco de dados
        feedback_id = save_feedback(st.session_state.user["id"], avg_rating, structured_comment)
        
        # Mensagem de confirmação
        confirmation_msg = f"✅ Feedback salvo com sucesso!\n\n📊 Resumo:\n• Produto: {feedback['product']}\n• Avaliação do produto: {feedback['product_rating']}/5\n• Avaliação da entrega: {feedback['delivery_rating']}/5\n• Média geral: {avg_rating:.1f}/5\n\nObrigado pelo seu feedback! 🙏\n\nDeseja fornecer outro feedback? (sim/não)"
        
        st.session_state.chat_history.append({"role": "assistant", "content": confirmation_msg})
        feedback["stage"] = 5
        
    elif feedback["stage"] == 5:
        # Verificar se o usuário quer dar outro feedback
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        if user_input.lower() in ["sim", "s", "yes", "y"]:
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": "Ótimo! Qual produto você gostaria de avaliar agora?"
            })
            st.session_state.current_feedback = {
                "stage": 1, 
                "product": None, 
                "product_rating": None, 
                "delivery_rating": None, 
                "comment": None
            }
        else:
            st.session_state.chat_history.append({
                "role": "assistant", 
                "content": "Obrigado por participar! 😊\n\nSe quiser ver seus feedbacks anteriores, acesse a seção de **Dashboard**.\n\nPara ver a fila de processamento, acesse **Fila de Processamento**."
            })
            st.session_state.current_feedback = {
                "stage": 0, 
                "product": None, 
                "product_rating": None, 
                "delivery_rating": None, 
                "comment": None
            }

# ==================== PÁGINAS ====================

def login_page():
    """Renderiza a página de login e registro."""
    st.title("🤖 FeedSmart")
    st.subheader("Sistema Inteligente de Coleta de Feedback")
    
    tab1, tab2 = st.tabs(["Login", "Registrar"])
    
    with tab1:
        st.subheader("Fazer Login")
        with st.form("login_form"):
            username = st.text_input("Nome de usuário")
            password = st.text_input("Senha", type="password")
            submit_button = st.form_submit_button("Entrar")
            
            if submit_button:
                if username and password:
                    user = verify_login(username, password)
                    if user:
                        st.session_state.user = user
                        st.session_state.page = 'home'
                        st.success("Login realizado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Nome de usuário ou senha incorretos")
                else:
                    st.error("Preencha todos os campos")
    
    with tab2:
        st.subheader("Criar Conta")
        with st.form("register_form"):
            new_username = st.text_input("Nome de usuário", key="reg_username")
            new_password = st.text_input("Senha", type="password", key="reg_password")
            confirm_password = st.text_input("Confirmar senha", type="password")
            name = st.text_input("Nome completo")
            email = st.text_input("Email")
            register_button = st.form_submit_button("Registrar")
            
            if register_button:
                if new_password != confirm_password:
                    st.error("As senhas não coincidem")
                else:
                    success, message = register_user(new_username, new_password, name, email)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

def home_page():
    """Renderiza a página inicial com informações e estatísticas."""
    st.title(f"Bem-vindo, {st.session_state.user['name']}! 👋")
    
    # Barra lateral com navegação
    with st.sidebar:
        st.title("🧭 Navegação")
        if st.button("🏠 Página Inicial"):
            change_page('home')
        if st.button("🤖 Chatbot de Feedback"):
            change_page('chatbot')
        if st.button("📊 Dashboard"):
            change_page('dashboard')
        if st.button("🔄 Fila de Processamento"):
            change_page('queue')
        
        st.divider()
        if st.button("🚪 Sair"):
            logout()
    
    st.markdown("""
    ### 🎯 Sobre o FeedSmart
    
    Este é um sistema inteligente de coleta de feedback que utiliza:
    - **Chatbot interativo** para uma experiência natural
    - **Algoritmos avançados** para organização eficiente
    - **Sistema de filas** com priorização automática
    - **Análise visual** para insights valiosos
    """)
    
    st.subheader("🚀 Funcionalidades Principais:")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **🤖 Chatbot de Feedback**
        - Conversa natural e intuitiva
        - Avaliação de produtos e entrega
        - Coleta de comentários detalhados
        
        **📊 Dashboard Analítico**
        - Visualização de todos os feedbacks
        - Gráficos de evolução temporal
        - Ordenação inteligente (Merge Sort)
        """)
    
    with col2:
        st.markdown("""
        **🔄 Fila de Processamento**
        - Organização automática por prioridade
        - Sistema FIFO (First In, First Out)
        - Controles de processamento
        
        **🔐 Sistema Seguro**
        - Autenticação criptografada
        - Dados pessoais protegidos
        - Sessões seguras
        """)
    
    # Estatísticas rápidas
    st.subheader("📈 Suas Estatísticas")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        queue_size = st.session_state.feedback_queue.size()
        st.metric("🔄 Feedbacks na Fila", queue_size)
    
    with col2:
        feedbacks = get_user_feedbacks(st.session_state.user["id"])
        total_feedbacks = len(feedbacks)
        st.metric("📝 Total de Feedbacks", total_feedbacks)
    
    with col3:
        if total_feedbacks > 0:
            avg_rating = feedbacks['rating'].mean()
            st.metric("⭐ Avaliação Média", f"{avg_rating:.1f}/5")
        else:
            st.metric("⭐ Avaliação Média", "N/A")
    
    with col4:
        if total_feedbacks > 0:
            last_feedback = feedbacks.iloc[0]['timestamp']
            last_date = pd.to_datetime(last_feedback).strftime('%d/%m/%Y')
            st.metric("📅 Último Feedback", last_date)
        else:
            st.metric("📅 Último Feedback", "N/A")
    
    # Call to action
    if total_feedbacks == 0:
        st.info("🎯 **Comece agora!** Clique em 'Chatbot de Feedback' para registrar sua primeira avaliação.")

def chatbot_page():
    """Renderiza a interface do chatbot para coleta de feedback."""
    st.title("🤖 Chatbot de Feedback")
    
    # Barra lateral com navegação
    with st.sidebar:
        st.title("🧭 Navegação")
        if st.button("🏠 Página Inicial"):
            change_page('home')
        if st.button("🤖 Chatbot de Feedback"):
            change_page('chatbot')
        if st.button("📊 Dashboard"):
            change_page('dashboard')
        if st.button("🔄 Fila de Processamento"):
            change_page('queue')
        
        st.divider()
        
        st.subheader("🛠️ Controles")
        if st.button("🗑️ Limpar Histórico", help="Limpa todo o histórico da conversa"):
            clear_chat_history()
            st.success("Histórico limpo com sucesso!")
            st.rerun()
        
        st.divider()
        if st.button("🚪 Sair"):
            logout()
    
    # Iniciar conversa se for a primeira vez
    if len(st.session_state.chat_history) == 0:
        process_chat_input("")
    
    # Container para o histórico do chat
    chat_container = st.container()
    with chat_container:
        for i, chat in enumerate(st.session_state.chat_history):
            if chat["role"] == "user":
                message(chat["content"], is_user=True, key=f"msg_{i}")
            else:
                message(chat["content"], is_user=False, key=f"msg_{i}")
    
    # Interface de entrada baseada no estágio atual
    feedback = st.session_state.current_feedback
    
    if feedback["stage"] == 1:
        # Seleção de produto
        st.subheader("Selecione o produto:")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_product = st.selectbox(
                "Escolha o produto que você adquiriu:",
                [""] + PRODUCTS,
                key="product_select"
            )
        
        with col2:
            st.write("")  # Espaçamento
            if st.button("Enviar", key="send_product"):
                if selected_product:
                    process_chat_input(selected_product)
                    st.rerun()
                else:
                    st.warning("Por favor, selecione um produto.")
    
    elif feedback["stage"] in [2, 3]:
        # Avaliação (produto ou entrega)
        stage_text = "produto" if feedback["stage"] == 2 else "entrega"
        st.subheader(f"Avalie a qualidade do {stage_text}:")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            rating = st.selectbox(
                f"Nota para {stage_text} (0-5):",
                [""] + list(range(6)),
                key=f"{stage_text}_rating_select"
            )
        
        with col2:
            st.write("")  # Espaçamento
            if st.button("Enviar", key=f"send_{stage_text}_rating"):
                if rating != "":
                    process_chat_input(str(rating))
                    st.rerun()
                else:
                    st.warning("Por favor, selecione uma avaliação.")
    
    elif feedback["stage"] == 4:
        # Comentário
        st.subheader("Comentário adicional:")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            comment = st.text_area(
                "Deixe seu comentário (opcional):",
                placeholder="Conte-nos mais sobre sua experiência...",
                key="comment_input",
                height=100
            )
        
        with col2:
            st.write("")  # Espaçamento
            st.write("")  # Mais espaçamento
            if st.button("Finalizar", key="send_comment"):
                process_chat_input(comment)
                st.rerun()
    
    elif feedback["stage"] == 5:
        # Confirmação para novo feedback
        st.subheader("Deseja dar outro feedback?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Sim, novo feedback"):
                process_chat_input("sim")
                st.rerun()
        
        with col2:
            if st.button("🏠 Voltar ao início"):
                change_page('home')
    
    else:
        # Input de texto padrão para outros casos
        user_input = st.text_input("Digite sua mensagem:", key="user_input")
        
        if st.button("Enviar") and user_input:
            process_chat_input(user_input)
            st.rerun()

def dashboard_page():
    """Renderiza o dashboard analítico com métricas e gráficos."""
    st.title("📊 Dashboard Analítico")
    
    # Barra lateral com navegação
    with st.sidebar:
        st.title("🧭 Navegação")
        if st.button("🏠 Página Inicial"):
            change_page('home')
        if st.button("🤖 Chatbot de Feedback"):
            change_page('chatbot')
        if st.button("📊 Dashboard"):
            change_page('dashboard')
        if st.button("🔄 Fila de Processamento"):
            change_page('queue')
        
        st.divider()
        if st.button("🚪 Sair"):
            logout()
    
    # Opções de ordenação
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("Seus Feedbacks")
    with col2:
        sort_option = st.selectbox(
            "Ordenar por:",
            ["Data (mais recente)", "Avaliação (maior para menor)"],
            key="sort_option"
        )
    
    sort_method = 'rating' if 'Avaliação' in sort_option else 'timestamp'
    
    # Obter feedbacks do usuário
    feedbacks = get_user_feedbacks(st.session_state.user["id"], sort_method)
    
    if len(feedbacks) == 0:
        st.info("📝 Você ainda não tem feedbacks registrados.")
        st.write("Vá para o **Chatbot de Feedback** para registrar sua primeira avaliação!")
        
        if st.button("🤖 Ir para Chatbot"):
            change_page('chatbot')
    else:
        # Calcular métricas
        avg_rating = feedbacks['rating'].mean()
        max_rating = feedbacks['rating'].max()
        min_rating = feedbacks['rating'].min()
        total_feedbacks = len(feedbacks)
        
        # Exibir métricas em cards
        st.subheader("📈 Estatísticas Gerais")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="📈 Avaliação Média",
                value=f"{avg_rating:.1f}/5",
                delta=f"{avg_rating - 3:.1f}" if avg_rating != 3 else None
            )
        
        with col2:
            st.metric(
                label="⭐ Maior Avaliação",
                value=f"{max_rating:.1f}/5"
            )
        
        with col3:
            st.metric(
                label="📉 Menor Avaliação",
                value=f"{min_rating:.1f}/5"
            )
        
        with col4:
            st.metric(
                label="📝 Total de Feedbacks",
                value=total_feedbacks
            )
        
        st.divider()
        
        # Gráfico de evolução
        if len(feedbacks) > 1:
            st.subheader("📈 Evolução das Avaliações")
            
            # Preparar dados para o gráfico
            feedbacks_sorted = feedbacks.copy()
            feedbacks_sorted['timestamp'] = pd.to_datetime(feedbacks_sorted['timestamp'])
            feedbacks_sorted = feedbacks_sorted.sort_values('timestamp')
            feedbacks_sorted['avg_rating_cumulative'] = feedbacks_sorted['rating'].expanding().mean()
            
            # Criar gráfico
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Linha principal
            ax.plot(
                range(len(feedbacks_sorted)), 
                feedbacks_sorted['avg_rating_cumulative'], 
                marker='o', 
                linewidth=2, 
                markersize=6, 
                color='#1f77b4',
                label='Média Cumulativa'
            )
            
            # Linha de referência (média geral)
            ax.axhline(
                y=avg_rating, 
                color='red', 
                linestyle='--', 
                alpha=0.7,
                label=f'Média Geral ({avg_rating:.1f})'
            )
            
            # Configurações do gráfico
            ax.set_xlabel('Feedback #')
            ax.set_ylabel('Avaliação')
            ax.set_title('Evolução da Média de Avaliações ao Longo do Tempo')
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.set_ylim(0, 5.5)
            
            # Exibir gráfico
            st.pyplot(fig)
            
        else:
            # Gráfico de barras para feedback único
            st.subheader("📊 Sua Avaliação")
            
            fig, ax = plt.subplots(figsize=(8, 6))
            
            categories = ['Sua Avaliação', 'Média Ideal']
            values = [feedbacks.iloc[0]['rating'], 5.0]
            colors = ['#1f77b4', '#90EE90']
            
            bars = ax.bar(categories, values, color=colors, alpha=0.7)
            
            # Adicionar valores nas barras
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{value:.1f}', ha='center', va='bottom', fontsize=12)
            
            ax.set_ylabel('Avaliação')
            ax.set_title('Comparação com Avaliação Ideal')
            ax.set_ylim(0, 5.5)
            ax.grid(True, alpha=0.3, axis='y')
            
            st.pyplot(fig)
        
        st.divider()
        
        # Tabela de feedbacks
        st.subheader(f"📋 Histórico Detalhado (Ordenado por {sort_option})")
        
        # Preparar dados para exibição
        display_df = feedbacks.copy()
        display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%d/%m/%Y %H:%M')
        display_df = display_df.rename(columns={
            'rating': 'Avaliação',
            'comment': 'Comentário',
            'timestamp': 'Data/Hora',
            'priority': 'Prioridade'
        })
        
        # Mapear prioridade para labels
        display_df['Prioridade'] = display_df['Prioridade'].map(PRIORITY_LABELS)
        
        # Exibir tabela
        st.dataframe(
            display_df[['Data/Hora', 'Avaliação', 'Prioridade', 'Comentário']],
            use_container_width=True,
            hide_index=True
        )

def queue_page():
    """Renderiza a página de gerenciamento da fila de processamento."""
    st.title("🔄 Fila de Processamento")
    
    # Barra lateral com navegação
    with st.sidebar:
        st.title("🧭 Navegação")
        if st.button("🏠 Página Inicial"):
            change_page('home')
        if st.button("🤖 Chatbot de Feedback"):
            change_page('chatbot')
        if st.button("📊 Dashboard"):
            change_page('dashboard')
        if st.button("🔄 Fila de Processamento"):
            change_page('queue')
        
        st.divider()
        if st.button("🚪 Sair"):
            logout()
    
    st.write("Esta página mostra os feedbacks na fila de processamento, organizados por prioridade.")
    
    queue = st.session_state.feedback_queue
    
    # Informações da fila
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📊 Itens na Fila", queue.size())
    
    with col2:
        next_item = queue.peek()
        if next_item:
            st.metric("⏭️ Próximo", f"Avaliação {next_item['rating']:.1f}/5")
        else:
            st.metric("⏭️ Próximo", "Fila vazia")
    
    with col3:
        if queue.size() > 0:
            sorted_items = queue.get_sorted_by_priority()
            highest_priority = sorted_items[0]['priority']
            st.metric("🚨 Maior Prioridade", PRIORITY_LABELS.get(highest_priority, "N/A"))
        else:
            st.metric("🚨 Maior Prioridade", "N/A")
    
    st.divider()
    
    # Controles da fila
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⚡ Processar Próximo", disabled=queue.is_empty()):
            processed = queue.process_next()
            if processed:
                st.success(f"✅ Feedback processado: Avaliação {processed['rating']:.1f}/5")
                st.rerun()
    
    with col2:
        if st.button("🗑️ Limpar Fila", disabled=queue.is_empty()):
            queue.clear()
            st.success("🧹 Fila limpa com sucesso!")
            st.rerun()
    
    st.divider()
    
    # Exibir itens da fila
    if queue.size() > 0:
        st.subheader("📋 Itens na Fila (Ordenados por Prioridade)")
        
        # Obter itens ordenados por prioridade
        sorted_items = queue.get_sorted_by_priority()
        
        # Criar DataFrame para exibição
        queue_data = []
        for item in sorted_items:
            # Converter timestamp para formato legível
            timestamp = datetime.datetime.strptime(item['timestamp'], "%Y-%m-%d %H:%M:%S")
            formatted_time = timestamp.strftime("%d/%m/%Y %H:%M")
            
            queue_data.append({
                "Data/Hora": formatted_time,
                "Avaliação": f"{item['rating']:.1f}/5",
                "Prioridade": PRIORITY_LABELS.get(item['priority'], "N/A"),
                "Comentário": item['comment'][:50] + "..." if len(item['comment']) > 50 else item['comment']
            })
        
        # Exibir tabela
        queue_df = pd.DataFrame(queue_data)
        st.dataframe(
            queue_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Estatísticas da fila
        st.subheader("📊 Estatísticas da Fila")
        
        # Contar por prioridade
        priority_counts = {}
        for item in sorted_items:
            priority = item['priority']
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
        
        # Exibir contadores
        cols = st.columns(5)
        for i, (priority, label) in enumerate(PRIORITY_LABELS.items()):
            with cols[i]:
                count = priority_counts.get(priority, 0)
                st.metric(label, count)
    
    else:
        # Fila vazia
        st.info("📭 A fila de processamento está vazia.")
        st.write("Novos feedbacks aparecerão aqui automaticamente quando forem registrados no chatbot.")
        
        if st.button("🤖 Ir para Chatbot"):
            change_page('chatbot')

# ==================== RENDERIZAÇÃO PRINCIPAL ====================

def main():
    """Função principal que controla o fluxo da aplicação."""
    # Verificar autenticação
    if st.session_state.user is None:
        login_page()
    else:
        # Renderizar página atual
        if st.session_state.page == 'home':
            home_page()
        elif st.session_state.page == 'chatbot':
            chatbot_page()
        elif st.session_state.page == 'dashboard':
            dashboard_page()
        elif st.session_state.page == 'queue':
            queue_page()
        else:
            # Página padrão
            home_page()

# Executar aplicação
if __name__ == "__main__":
    main()
