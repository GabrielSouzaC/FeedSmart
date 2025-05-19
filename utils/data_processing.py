import pandas as pd
import os
import datetime

# Caminho para o arquivo CSV
DATA_FILE = 'data/feedback_data.csv'

def ensure_data_file_exists():
    """Garante que o arquivo de dados existe e tem a estrutura correta."""
    if not os.path.exists('data'):
        os.makedirs('data')
    
    if not os.path.exists(DATA_FILE):
        # Criar um DataFrame vazio com as colunas necessárias
        df = pd.DataFrame(columns=[
            'nome', 'email', 'produto', 'avaliacao_produto', 
            'avaliacao_entrega', 'avaliacao_atendimento', 
            'comentario', 'data'
        ])
        df.to_csv(DATA_FILE, index=False)

def load_feedback_data():
    """Carrega os dados de feedback do arquivo CSV."""
    ensure_data_file_exists()
    return pd.read_csv(DATA_FILE)

def save_feedback(feedback_data):
    """Salva um novo feedback no arquivo CSV."""
    ensure_data_file_exists()
    
    # Carregar dados existentes
    df = load_feedback_data()
    
    # Adicionar novo feedback
    new_row = pd.DataFrame([feedback_data])
    df = pd.concat([df, new_row], ignore_index=True)
    
    # Salvar de volta no arquivo
    df.to_csv(DATA_FILE, index=False)
    
    return True

def process_feedback(df):
    """Processa os dados de feedback para análise."""
    if df.empty:
        return df
    
    # Calcular médias de avaliação
    df['avaliacao_media'] = df[['avaliacao_produto', 'avaliacao_entrega', 'avaliacao_atendimento']].mean(axis=1)
    
    # Converter coluna de data para datetime
    df['data'] = pd.to_datetime(df['data'])
    
    # Adicionar categorias de satisfação
    def categorize_satisfaction(rating):
        if rating <= 2:
            return "Insatisfeito"
        elif rating <= 3.5:
            return "Neutro"
        else:
            return "Satisfeito"
    
    df['categoria_satisfacao'] = df['avaliacao_media'].apply(categorize_satisfaction)
    
    return df