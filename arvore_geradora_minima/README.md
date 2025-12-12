# Árvore Geradora Mínima (AGM)

## Descrição do Problema

Dado um grafo não-direcionado, conexo e ponderado, encontre a árvore geradora mínima (AGM) deste grafo. A árvore geradora mínima é um subconjunto das arestas que conecta todos os vértices sem formar ciclos e com o menor peso total possível.

Você deve implementar um algoritmo (como Kruskal ou Prim) para encontrar a AGM e retornar o peso total da árvore geradora mínima.

## Entrada

A primeira linha contém dois inteiros **n** e **m**, onde:

- **n** é o número de vértices (1 <= n <= 1000)
- **m** é o número de arestas (1 <= m <= 10000)

As próximas **m** linhas contêm três inteiros cada: **u**, **v** e **w**, representando uma aresta entre os vértices **u** e **v** com peso **w**.

### Restrições:

- 1 <= n <= 1000
- 1 <= m <= 10000
- 1 <= u, v <= n
- 1 <= w <= 100000
- O grafo é conexo
- Não há arestas múltiplas ou loops

## Saída

Imprima um único inteiro representando o peso total da árvore geradora mínima.

## Exemplo

### Entrada:
```
4 5
1 2 10
2 3 20
3 4 30
4 1 40
1 3 50
```

### Saída:
```
60
```

### Explicação:

O grafo possui 4 vértices e 5 arestas. A árvore geradora mínima pode ser formada pelas arestas:

- Aresta (1,2) com peso 10
- Aresta (2,3) com peso 20
- Aresta (3,4) com peso 30

Peso total: 10 + 20 + 30 = 60

## Dicas de Implementação

- Use o algoritmo de Kruskal com Union-Find para uma implementação eficiente
- Alternativamente, implemente o algoritmo de Prim com uma fila de prioridade
- Lembre-se de ordenar as arestas por peso no algoritmo de Kruskal
- Certifique-se de que o grafo seja conexo antes de processar

## Algoritmos Sugeridos

### Algoritmo de Kruskal

1. Ordene todas as arestas por peso crescente
2. Use Union-Find para detectar ciclos
3. Para cada aresta, se não formar ciclo, adicione à AGM

### Algoritmo de Prim

1. Comece com um vértice qualquer
2. Mantenha uma fila de prioridade com arestas candidatas
3. Sempre escolha a aresta de menor peso que conecta a um novo vértice