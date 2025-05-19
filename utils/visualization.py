import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def create_category_chart(df):
    """Cria um gráfico de barras para as avaliações por categoria."""
    # Calcular médias
    avg_produto = df['avaliacao_produto'].mean()
    avg_entrega = df['avaliacao_entrega'].mean()
    avg_atendimento = df['avaliacao_atendimento'].mean()
    
    # Criar figura
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Dados para o gráfico
    categorias = ['Produto', 'Entrega', 'Atendimento']
    valores = [avg_produto, avg_entrega, avg_atendimento]
    cores = ['#3498db', '#2ecc71', '#e74c3c']
    
    # Criar barras
    bars = ax.bar(categorias, valores, color=cores, width=0.6)
    
    # Adicionar valores nas barras
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.1f}', ha='center', va='bottom')
    
    # Configurar eixos
    ax.set_ylim(0, 5.5)
    ax.set_ylabel('Avaliação Média (1-5)')
    ax.set_title('Avaliação Média por Categoria')
    
    # Adicionar linha de referência
    ax.axhline(y=3, color='gray', linestyle='--', alpha=0.7)
    
    # Estilo
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    return fig

def create_satisfaction_chart(df):
    """Cria um gráfico de pizza para a distribuição de satisfação."""
    # Calcular médias e categorizar
    df['avaliacao_media'] = df[['avaliacao_produto', 'avaliacao_entrega', 'avaliacao_atendimento']].mean(axis=1)
    
    def categorize_satisfaction(rating):
        if rating <= 2:
            return "Insatisfeito"
        elif rating <= 3.5:
            return "Neutro"
        else:
            return "Satisfeito"
    
    df['categoria_satisfacao'] = df['avaliacao_media'].apply(categorize_satisfaction)
    
    # Contar ocorrências
    satisfaction_counts = df['categoria_satisfacao'].value_counts()
    
    # Criar figura
    fig, ax = plt.subplots(figsize=(8, 8))
    
    # Cores
    colors = ['#e74c3c', '#f39c12', '#2ecc71']
    
    # Criar gráfico de pizza
    wedges, texts, autotexts = ax.pie(
        satisfaction_counts, 
        labels=satisfaction_counts.index, 
        autopct='%1.1f%%',
        startangle=90,
        colors=colors,
        wedgeprops={'edgecolor': 'white', 'linewidth': 2}
    )
    
    # Estilo dos textos
    for text in texts:
        text.set_fontsize(12)
    for autotext in autotexts:
        autotext.set_fontsize(12)
        autotext.set_fontweight('bold')
        autotext.set_color('white')
    
    # Título
    ax.set_title('Distribuição de Satisfação dos Clientes', fontsize=14)
    
    # Círculo no centro para efeito de donut
    centre_circle = plt.Circle((0, 0), 0.5, fc='white')
    ax.add_artist(centre_circle)
    
    # Igual aspecto para garantir círculo
    ax.set_aspect('equal')
    
    plt.tight_layout()
    return fig