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
            # Aqui poderia haver lógica adicional para processar o feedback
            return next_feedback
        return None