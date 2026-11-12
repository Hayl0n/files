# Tema 2 – Minimização e Otimização de AFD (Grupo 2)

UERN – Ciência da Computação – MDI0196 Linguagens Formais e Autômatos (2026.2)

Requisitos: Python 3.8+ (somente biblioteca padrão). Graphviz é opcional (para desenhar o .dot).

## Arquivos
| Arquivo | Conteúdo |
|---|---|
| `afd.py` | Classe `AFD`, remoção de inalcançáveis/inúteis, minimização (Moore), tabela de pares, equivalência |
| `minilang.py` | Mini-linguagem MiniPT: AFDs por token, união por produto, tokenizer |
| `main.py` | Menu interativo e linha de comando |
| `testes.py` | 15 testes automatizados |
| `exemplos/` | AFDs em JSON e programas `.mini` |

## Como executar
```
python main.py                 # menu interativo
python main.py demo            # demonstração completa
python main.py minimizar exemplos/afd_exemplo.json -w 01 0101 --dot saida.dot
python main.py lexer exemplos/programa.mini
python main.py lexer --texto "var x = 3.5;"
python main.py lexer-info
python testes.py               # roda os testes
dot -Tpng saida.dot -o saida.png   # (opcional) desenhar o AFD
```

## Formato JSON do AFD
```json
{"alfabeto":["0","1"], "estados":["A","B"], "inicial":"A", "finais":["B"],
 "transicoes":{"A":{"0":"B","1":"A"}, "B":{"0":"B"}}}
```
Transições ausentes = AFD parcial (o programa completa com estado de erro internamente).
