"""
main.py - Interface de linha de comando.

Uso:
  python main.py                       # menu interativo
  python main.py demo                  # demonstração completa
  python main.py minimizar ARQ.json [-w PALAVRA ...] [--dot SAIDA.dot]
  python main.py lexer ARQ.mini        # tokeniza um arquivo
  python main.py lexer --texto "var x = 3;"
  python main.py lexer-info            # estatísticas do AFD do tokenizer
"""

import argparse
import os
import sys

from afd import AFD
from minilang import AnalisadorLexico

DIR = os.path.dirname(os.path.abspath(__file__))
EXEMPLO_AFD = os.path.join(DIR, "exemplos", "afd_exemplo.json")
EXEMPLO_PROG = os.path.join(DIR, "exemplos", "programa.mini")


def titulo(txt):
    print("\n" + "=" * 70 + f"\n{txt}\n" + "=" * 70)


# ----------------------------------------------------------------------
# Minimização
# ----------------------------------------------------------------------
def cmd_minimizar(caminho, palavras=(), dot=None):
    afd = AFD.de_json(caminho)
    titulo(f"AFD ORIGINAL ({len(afd.estados)} estados) - {os.path.basename(caminho)}")
    print(afd.tabela_texto())

    minimo, rel = afd.minimizar()

    titulo("PASSO 1 - Estados inalcançáveis")
    print("Removidos:", ", ".join(rel["inalcancaveis"]) or "(nenhum)")

    titulo("PASSO 2 - Refinamento de partições (estados equivalentes)")
    if rel["morto_adicionado"]:
        print("(AFD parcial: estado de erro '∅' adicionado para completar δ)")
    for i, p in enumerate(rel["passos"]):
        print(f"  P{i}: {p}" + ("   <- partição inicial (finais x não-finais)" if i == 0 else ""))
    print(f"  P{len(rel['passos'])}: igual a P{len(rel['passos']) - 1}  -> estável")
    print("\nClasses de equivalência (cada uma vira um estado do AFD mínimo):")
    for novo, membros in rel["classes"].items():
        print(f"  {novo} = {{{', '.join(membros)}}}")
    if rel["mortos_removidos"]:
        print("Estado(s) morto(s) removido(s):",
              "; ".join("{" + ",".join(m) + "}" for m in rel["mortos_removidos"]))

    titulo(f"AFD MÍNIMO ({len(minimo.estados)} estados)")
    print(minimo.tabela_texto())
    print(f"\nReduzidos de {rel['estados_originais']} para {rel['estados_minimo']} estados. "
          f"Equivalente ao original? {afd.equivalente_a(minimo)}")

    if palavras:
        titulo("TESTE DE PALAVRAS")
        for p in palavras:
            o, m = afd.aceita(p), minimo.aceita(p)
            print(f"  '{p}': original={'ACEITA' if o else 'REJEITA'}  "
                  f"mínimo={'ACEITA' if m else 'REJEITA'}")
    if dot:
        with open(dot, "w", encoding="utf-8") as f:
            f.write(minimo.para_dot("AFD minimo"))
        print(f"\nGraphviz salvo em {dot}")


# ----------------------------------------------------------------------
# Analisador léxico
# ----------------------------------------------------------------------
def mostrar_tokens(texto, lex):
    tokens, erros = lex.tokenizar(texto)
    print(f"{'LINHA:COL':<10}{'TIPO':<20}LEXEMA")
    print("-" * 50)
    for t in tokens:
        print(f"{t.linha}:{t.coluna:<8}{t.tipo:<20}{t.lexema}")
    print(f"\n{len(tokens)} token(s), {len(erros)} erro(s) léxico(s).")
    for e in erros:
        print("  ", e)
    return tokens, erros


def cmd_lexer_info():
    lex = AnalisadorLexico()
    rel = lex.relatorio
    titulo("AFD DO ANALISADOR LÉXICO")
    print(f"Estados do AFD (união por produto) : {len(lex.afd_original.estados)}")
    print(f"Estados do AFD mínimo              : {len(lex.afd.estados)}")
    print(f"Inalcançáveis removidos            : {len(rel['inalcancaveis'])}")
    red = 100 * (1 - len(lex.afd.estados) / len(lex.afd_original.estados))
    print(f"Redução                            : {red:.1f}%")
    print(f"Transições antes/depois            : {len(lex.afd_original.delta)} / {len(lex.afd.delta)}")
    print(f"Equivalente ao original            : {lex.afd_original.equivalente_a(lex.afd)}")
    tipos = {}
    for f in lex.afd.finais:
        tipos[lex.afd.rotulos[f]] = tipos.get(lex.afd.rotulos[f], 0) + 1
    print("Estados finais por tipo de token   :", dict(sorted(tipos.items())))


def cmd_lexer(arquivo=None, texto=None):
    if arquivo:
        with open(arquivo, encoding="utf-8") as f:
            texto = f.read()
    if texto is None:
        print("Digite o código (linha vazia para terminar):")
        linhas = []
        while True:
            try:
                l = input()
            except EOFError:
                break
            if not l:
                break
            linhas.append(l)
        texto = "\n".join(linhas)
    lex = AnalisadorLexico()
    titulo("ANÁLISE LÉXICA (AFD mínimo)")
    mostrar_tokens(texto, lex)


# ----------------------------------------------------------------------
# Demonstração e menu
# ----------------------------------------------------------------------
def cmd_demo():
    cmd_minimizar(EXEMPLO_AFD, palavras=["", "1", "01", "0101", "11"])
    cmd_lexer_info()
    with open(EXEMPLO_PROG, encoding="utf-8") as f:
        texto = f.read()
    titulo("CÓDIGO-FONTE DE EXEMPLO")
    print(texto)
    titulo("ANÁLISE LÉXICA")
    mostrar_tokens(texto, AnalisadorLexico())
    titulo("ANÁLISE LÉXICA COM ERROS")
    erro = os.path.join(DIR, "exemplos", "programa_com_erros.mini")
    with open(erro, encoding="utf-8") as f:
        mostrar_tokens(f.read(), AnalisadorLexico())


def menu():
    while True:
        print("\n=== Tema 2 - Minimização de AFD e Analisador Léxico ===")
        print("1) Minimizar AFD de um arquivo JSON")
        print("2) Minimizar o AFD de exemplo")
        print("3) Tokenizar um arquivo da mini-linguagem")
        print("4) Digitar código e tokenizar")
        print("5) Estatísticas do AFD do analisador léxico")
        print("6) Demonstração completa")
        print("0) Sair")
        op = input("Opção: ").strip()
        try:
            if op == "1":
                cmd_minimizar(input("Caminho do JSON: ").strip(),
                              input("Palavras para testar (separadas por espaço, ENTER p/ nenhuma): ").split())
            elif op == "2":
                cmd_minimizar(EXEMPLO_AFD, ["", "1", "01", "0101"])
            elif op == "3":
                cmd_lexer(arquivo=input("Caminho do arquivo: ").strip())
            elif op == "4":
                cmd_lexer()
            elif op == "5":
                cmd_lexer_info()
            elif op == "6":
                cmd_demo()
            elif op == "0":
                return
            else:
                print("Opção inválida.")
        except (OSError, ValueError, KeyError) as e:
            print(f"Erro: {e}")


def main():
    ap = argparse.ArgumentParser(description="Minimização de AFD e Analisador Léxico")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("lexer-info")
    m = sub.add_parser("minimizar")
    m.add_argument("arquivo")
    m.add_argument("-w", "--palavras", nargs="*", default=[])
    m.add_argument("--dot")
    l = sub.add_parser("lexer")
    l.add_argument("arquivo", nargs="?")
    l.add_argument("--texto")
    args = ap.parse_args()

    if args.cmd == "demo":
        cmd_demo()
    elif args.cmd == "lexer-info":
        cmd_lexer_info()
    elif args.cmd == "minimizar":
        cmd_minimizar(args.arquivo, args.palavras, args.dot)
    elif args.cmd == "lexer":
        cmd_lexer(args.arquivo, args.texto)
    else:
        menu()


if __name__ == "__main__":
    sys.exit(main())
