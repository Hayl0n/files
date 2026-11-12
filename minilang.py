"""
minilang.py - Analisador Léxico (Tokenizer) da mini-linguagem "MiniPT".

O analisador é dirigido por UM ÚNICO AFD, construído assim:
  1. um AFD pequeno para cada categoria de token (palavras reservadas,
     identificadores, números, operadores, strings, comentários...);
  2. união dos AFDs por construção de produto, com prioridade
     (palavra reservada vence identificador);
  3. minimização (afd.py) preservando o tipo de token de cada estado final;
  4. execução com a regra do "maior casamento" (maximal munch).

Categorias de token:
  PALAVRA_RESERVADA  se senao enquanto para funcao retorne var imprima e ou nao
                     verdadeiro falso
  IDENTIFICADOR      [A-Za-z_][A-Za-z0-9_]*
  NUMERO_INTEIRO     [0-9]+
  NUMERO_REAL        [0-9]+ . [0-9]+
  STRING             " ... " (sem quebra de linha)
  OP_ARITMETICO      + - * / %
  OP_RELACIONAL      == != < <= > >=
  ATRIBUICAO         =
  DELIMITADOR        ( ) { } , ;
  COMENTARIO         // até o fim da linha   (descartado)
  ESPACO             espaços, tabs, quebras de linha (descartado)
"""

import string
from collections import deque
from afd import AFD

# ----------------------------------------------------------------------
# Alfabeto (símbolos fora dele são mapeados para "OUTRO")
# ----------------------------------------------------------------------
LETRAS = string.ascii_letters
DIGITOS = string.digits
SIMBOLOS = '+-*/%=!<>(){},;."_'
ESPACOS = " \t\r\n"
OUTRO = "OUTRO"
ALFABETO = list(LETRAS + DIGITOS + SIMBOLOS + ESPACOS) + [OUTRO]

PALAVRAS_RESERVADAS = ["se", "senao", "enquanto", "para", "funcao", "retorne",
                       "var", "imprima", "e", "ou", "nao", "verdadeiro", "falso"]
OPS_ARITMETICOS = ["+", "-", "*", "/", "%"]
OPS_RELACIONAIS = ["==", "!=", "<", "<=", ">", ">="]
DELIMITADORES = ["(", ")", "{", "}", ",", ";"]

DESCARTAVEIS = {"ESPACO", "COMENTARIO"}


def classificar(ch):
    """Converte um caractere do texto em símbolo do alfabeto do AFD."""
    return ch if ch in ALFABETO else OUTRO


# ----------------------------------------------------------------------
# AFDs de cada categoria (parciais: transições ausentes = erro)
# ----------------------------------------------------------------------
def _montar(delta, inicial, finais):
    estados = {inicial} | set(finais)
    for (s, _), t in delta.items():
        estados |= {s, t}
    return AFD(sorted(estados), ALFABETO, delta, inicial, finais)


def afd_literal(palavra):
    """Reconhece exatamente `palavra`."""
    delta = {(i, c): i + 1 for i, c in enumerate(palavra)}
    return _montar(delta, 0, {len(palavra)})


def afd_identificador():
    delta = {}
    for c in LETRAS + "_":
        delta[(0, c)] = 1
    for c in LETRAS + DIGITOS + "_":
        delta[(1, c)] = 1
    return _montar(delta, 0, {1})


def afd_inteiro():
    delta = {(0, d): 1 for d in DIGITOS}
    delta.update({(1, d): 1 for d in DIGITOS})
    return _montar(delta, 0, {1})


def afd_real():
    delta = {(0, d): 1 for d in DIGITOS}
    delta.update({(1, d): 1 for d in DIGITOS})
    delta[(1, ".")] = 2
    delta.update({(2, d): 3 for d in DIGITOS})
    delta.update({(3, d): 3 for d in DIGITOS})
    return _montar(delta, 0, {3})


def afd_string():
    delta = {(0, '"'): 1, (1, '"'): 2}
    for c in ALFABETO:
        if c not in ('"', "\n", "\r"):
            delta[(1, c)] = 1
    return _montar(delta, 0, {2})


def afd_comentario():
    delta = {(0, "/"): 1, (1, "/"): 2}
    for c in ALFABETO:
        if c not in ("\n", "\r"):
            delta[(2, c)] = 2
    return _montar(delta, 0, {2})


def afd_espaco():
    delta = {(0, c): 1 for c in ESPACOS}
    delta.update({(1, c): 1 for c in ESPACOS})
    return _montar(delta, 0, {1})


# ----------------------------------------------------------------------
# União por produto com prioridade
# ----------------------------------------------------------------------
def uniao(componentes):
    """
    componentes: lista [(AFD, tipo_de_token)] em ORDEM DE PRIORIDADE.
    Retorna um AFD único cujos estados finais carregam o tipo do token de
    maior prioridade entre os componentes que aceitam.
    """
    inicio = tuple(a.inicial for a, _ in componentes)
    ids = {inicio: 0}
    fila = deque([inicio])
    delta, rotulos = {}, {}
    while fila:
        tupla = fila.popleft()
        for i, (a, tipo) in enumerate(componentes):
            if tupla[i] is not None and tupla[i] in a.finais:
                rotulos[ids[tupla]] = tipo  # primeiro da lista = maior prioridade
                break
        for sim in ALFABETO:
            prox = tuple(
                a.delta.get((s, sim)) if s is not None else None
                for (a, _), s in zip(componentes, tupla)
            )
            if all(p is None for p in prox):
                continue  # estado morto: não é criado
            if prox not in ids:
                ids[prox] = len(ids)
                fila.append(prox)
            delta[(ids[tupla], sim)] = ids[prox]
    return AFD(list(ids.values()), ALFABETO, delta, 0, set(rotulos), rotulos)


def construir_afd_lexico():
    """Monta o AFD (não minimizado) da mini-linguagem."""
    comps = [(afd_literal(p), "PALAVRA_RESERVADA") for p in PALAVRAS_RESERVADAS]
    comps += [(afd_identificador(), "IDENTIFICADOR"),
              (afd_real(), "NUMERO_REAL"),
              (afd_inteiro(), "NUMERO_INTEIRO"),
              (afd_string(), "STRING"),
              (afd_comentario(), "COMENTARIO"),
              (afd_espaco(), "ESPACO")]
    comps += [(afd_literal(o), "OP_ARITMETICO") for o in OPS_ARITMETICOS]
    comps += [(afd_literal(o), "OP_RELACIONAL") for o in OPS_RELACIONAIS]
    comps += [(afd_literal("="), "ATRIBUICAO")]
    comps += [(afd_literal(d), "DELIMITADOR") for d in DELIMITADORES]
    return uniao(comps)


# ----------------------------------------------------------------------
# Tokens e analisador léxico
# ----------------------------------------------------------------------
class Token:
    def __init__(self, tipo, lexema, linha, coluna):
        self.tipo, self.lexema, self.linha, self.coluna = tipo, lexema, linha, coluna

    def __repr__(self):
        return f"Token({self.tipo}, {self.lexema!r}, {self.linha}:{self.coluna})"


class ErroLexico:
    def __init__(self, mensagem, lexema, linha, coluna):
        self.mensagem, self.lexema, self.linha, self.coluna = mensagem, lexema, linha, coluna

    def __str__(self):
        return f"Erro léxico em {self.linha}:{self.coluna} - {self.mensagem} ({self.lexema!r})"


class AnalisadorLexico:
    """Tokenizer dirigido por AFD. Use otimizar=False para usar o AFD sem minimizar."""

    def __init__(self, otimizar=True):
        bruto = construir_afd_lexico()
        self.afd_original = bruto
        if otimizar:
            self.afd, self.relatorio = bruto.minimizar()
        else:
            self.afd, self.relatorio = bruto, None

    def tokenizar(self, texto, manter_descartaveis=False):
        """Retorna (lista_de_tokens, lista_de_erros)."""
        tokens, erros = [], []
        n, pos, linha, col = len(texto), 0, 1, 1

        def avancar(lexema):
            nonlocal linha, col
            for ch in lexema:
                if ch == "\n":
                    linha, col = linha + 1, 1
                else:
                    col += 1

        while pos < n:
            estado, i, ultimo = self.afd.inicial, pos, None
            while i < n:
                prox = self.afd.delta.get((estado, classificar(texto[i])))
                if prox is None:
                    break
                estado, i = prox, i + 1
                if estado in self.afd.finais:
                    ultimo = (i, self.afd.rotulos[estado])  # maior casamento até agora
            if ultimo:
                fim, tipo = ultimo
                lexema = texto[pos:fim]
                if manter_descartaveis or tipo not in DESCARTAVEIS:
                    tokens.append(Token(tipo, lexema, linha, col))
                avancar(lexema)
                pos = fim
            else:
                if texto[pos] == '"':  # string sem fechamento: consome até fim da linha
                    fim = texto.find("\n", pos)
                    fim = n if fim == -1 else fim
                    lexema = texto[pos:fim]
                    erros.append(ErroLexico("string não fechada", lexema, linha, col))
                else:
                    lexema = texto[pos]
                    erros.append(ErroLexico("caractere inválido", lexema, linha, col))
                avancar(lexema)
                pos += len(lexema)
        return tokens, erros
