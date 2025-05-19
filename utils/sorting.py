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