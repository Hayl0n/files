"""Testes automatizados. Execute: python testes.py"""

import itertools
import os
import random
import unittest

from afd import AFD
from minilang import AnalisadorLexico

DIR = os.path.dirname(os.path.abspath(__file__))


def palavras(alfabeto, max_len):
    for n in range(max_len + 1):
        for p in itertools.product(alfabeto, repeat=n):
            yield "".join(p)


class TesteMinimizacao(unittest.TestCase):
    def setUp(self):
        self.afd = AFD.de_json(os.path.join(DIR, "exemplos", "afd_exemplo.json"))

    def test_inalcancaveis(self):
        sem = self.afd.remover_inalcancaveis()
        self.assertEqual(set(sem.estados), {"A", "B", "C", "E", "F", "G", "H"})

    def test_minimo_classico(self):
        minimo, rel = self.afd.minimizar()
        self.assertEqual(len(minimo.estados), 5)
        classes = sorted(sorted(c) for c in rel["classes"].values())
        self.assertEqual(classes, [["A", "E"], ["B", "H"], ["C"], ["F"], ["G"]])
        self.assertEqual(sorted(rel["inalcancaveis"]), ["D", "I"])

    def test_linguagem_preservada(self):
        minimo, _ = self.afd.minimizar()
        for p in palavras("01", 8):
            self.assertEqual(self.afd.aceita(p), minimo.aceita(p), p)
        self.assertTrue(self.afd.equivalente_a(minimo))

    def test_idempotente(self):
        m1, _ = self.afd.minimizar()
        m2, _ = m1.minimizar()
        self.assertEqual(len(m1.estados), len(m2.estados))

    def test_parcial(self):
        afd = AFD.de_json(os.path.join(DIR, "exemplos", "afd_parcial.json"))
        minimo, _ = afd.minimizar()
        self.assertEqual(len(minimo.estados), 3)  # q0 -a-> q1 -(b|c)*-> q1 -d-> q2
        for p in palavras("abcd", 6):
            self.assertEqual(afd.aceita(p), minimo.aceita(p), p)

    def test_linguagem_vazia_e_universal(self):
        vazio = AFD(["x", "y"], "ab", {("x", "a"): "y", ("y", "a"): "x"}, "x", [])
        m, _ = vazio.minimizar()
        self.assertEqual(len(m.estados), 1)
        self.assertFalse(m.aceita("") or m.aceita("a"))
        tudo = AFD(["x", "y"], "ab",
                   {("x", "a"): "y", ("x", "b"): "y", ("y", "a"): "x", ("y", "b"): "x"},
                   "x", ["x", "y"])
        m, _ = tudo.minimizar()
        self.assertEqual(len(m.estados), 1)

    def test_aleatorios(self):
        """Moore == tabela de pares == linguagem preservada, em 300 AFDs aleatórios."""
        rnd = random.Random(2026)
        for _ in range(300):
            n = rnd.randint(1, 9)
            estados = [f"s{i}" for i in range(n)]
            delta = {(s, a): rnd.choice(estados) for s in estados for a in "ab"
                     if rnd.random() < 0.9}  # alguns AFDs ficam parciais
            finais = [s for s in estados if rnd.random() < 0.4]
            afd = AFD(estados, "ab", delta, "s0", finais)
            minimo, rel = afd.minimizar(manter_morto=True)
            # a) mesma linguagem
            for p in palavras("ab", 6):
                self.assertEqual(afd.aceita(p), minimo.aceita(p))
            # b) quantidade de estados = nº de classes do table-filling
            comp = afd.remover_inalcancaveis().completar()
            pares = afd.pares_equivalentes()
            classes = {s: {s} for s in comp.estados}
            for p in pares:
                s, t = tuple(p)
                uniao = classes[s] | classes[t]
                for x in uniao:
                    classes[x] = uniao
            n_classes = len({frozenset(c) for c in classes.values()})
            self.assertEqual(len(minimo.estados), n_classes)
            # c) o mínimo não tem equivalentes nem inalcançáveis
            self.assertEqual(minimo.pares_equivalentes(), set())
            self.assertEqual(len(minimo.alcancaveis()), len(minimo.estados))


class TesteLexico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lex = AnalisadorLexico(otimizar=True)
        cls.lex_bruto = AnalisadorLexico(otimizar=False)

    def tipos(self, texto):
        toks, erros = self.lex.tokenizar(texto)
        return [(t.tipo, t.lexema) for t in toks], erros

    def test_minimizacao_reduz(self):
        self.assertLess(len(self.lex.afd.estados), len(self.lex.afd_original.estados))
        self.assertTrue(self.lex.afd_original.equivalente_a(self.lex.afd))

    def test_palavras_reservadas_vs_identificadores(self):
        toks, erros = self.tipos("se sena senao enquanto2 e ou")
        self.assertEqual(toks, [
            ("PALAVRA_RESERVADA", "se"), ("IDENTIFICADOR", "sena"),
            ("PALAVRA_RESERVADA", "senao"), ("IDENTIFICADOR", "enquanto2"),
            ("PALAVRA_RESERVADA", "e"), ("PALAVRA_RESERVADA", "ou")])
        self.assertEqual(erros, [])

    def test_numeros_e_operadores(self):
        toks, _ = self.tipos("x<=12.5+7 == y != 3")
        self.assertEqual(toks, [
            ("IDENTIFICADOR", "x"), ("OP_RELACIONAL", "<="), ("NUMERO_REAL", "12.5"),
            ("OP_ARITMETICO", "+"), ("NUMERO_INTEIRO", "7"), ("OP_RELACIONAL", "=="),
            ("IDENTIFICADOR", "y"), ("OP_RELACIONAL", "!="), ("NUMERO_INTEIRO", "3")])

    def test_atribuicao_string_comentario(self):
        toks, _ = self.tipos('var s = "oi mundo"; // comentario\n x = 1;')
        self.assertEqual([t for t, _ in toks], [
            "PALAVRA_RESERVADA", "IDENTIFICADOR", "ATRIBUICAO", "STRING", "DELIMITADOR",
            "IDENTIFICADOR", "ATRIBUICAO", "NUMERO_INTEIRO", "DELIMITADOR"])

    def test_divisao_vs_comentario(self):
        toks, _ = self.tipos("a / b // c")
        self.assertEqual([t for t, _ in toks], ["IDENTIFICADOR", "OP_ARITMETICO", "IDENTIFICADOR"])

    def test_posicoes(self):
        toks, _ = self.lex.tokenizar("var x;\n  y = 2;")
        y = [t for t in toks if t.lexema == "y"][0]
        self.assertEqual((y.linha, y.coluna), (2, 3))

    def test_erros(self):
        toks, erros = self.lex.tokenizar('a @ b\n"aberta\nc')
        self.assertEqual([(e.mensagem, e.linha, e.coluna) for e in erros],
                         [("caractere inválido", 1, 3), ("string não fechada", 2, 1)])
        self.assertEqual([t.lexema for t in toks], ["a", "b", "c"])

    def test_otimizado_igual_ao_bruto(self):
        with open(os.path.join(DIR, "exemplos", "programa.mini"), encoding="utf-8") as f:
            texto = f.read()
        a, ea = self.lex.tokenizar(texto, manter_descartaveis=True)
        b, eb = self.lex_bruto.tokenizar(texto, manter_descartaveis=True)
        self.assertEqual([(t.tipo, t.lexema, t.linha, t.coluna) for t in a],
                         [(t.tipo, t.lexema, t.linha, t.coluna) for t in b])
        self.assertEqual(ea, [])
        self.assertEqual(eb, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
