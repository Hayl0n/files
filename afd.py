"""
afd.py - Representação de AFD e algoritmos de otimização.

Tema 2 - Minimização e Otimização de Autômatos Finitos Determinísticos
Disciplina: Linguagens Formais e Autômatos (MDI0196) - UERN

Conteúdo:
  * classe AFD (5-upla (Q, Σ, δ, q0, F) + rótulos opcionais nos estados finais);
  * eliminação de estados inalcançáveis;
  * completar o AFD (estado de erro/morto);
  * eliminação de estados inúteis (que não levam a nenhum estado final);
  * minimização por refinamento de partições (algoritmo de Moore);
  * verificação cruzada pelo algoritmo da tabela de pares (table-filling);
  * teste de equivalência entre dois AFDs;
  * exportação para tabela de texto e Graphviz (.dot).

Os "rótulos" permitem que cada estado final carregue uma informação extra
(por exemplo, o tipo de token). Na minimização, dois estados finais só são
equivalentes se tiverem o MESMO rótulo; isso é o que permite minimizar o AFD
de um analisador léxico sem perder a distinção entre os tipos de token.
"""

from collections import deque
from itertools import combinations
import json


class AFD:
    """Autômato Finito Determinístico (pode ser parcial: δ não precisa ser total)."""

    def __init__(self, estados, alfabeto, delta, inicial, finais, rotulos=None):
        """
        estados : iterável de estados (qualquer objeto hasheável)
        alfabeto: iterável de símbolos (strings)
        delta   : dict {(estado, símbolo): estado}
        inicial : estado inicial
        finais  : iterável de estados finais
        rotulos : dict {estado_final: rótulo}; padrão "ACEITA"
        """
        self.estados = list(dict.fromkeys(estados))  # mantém ordem, sem repetição
        self.alfabeto = sorted(set(alfabeto))
        self.delta = dict(delta)
        self.inicial = inicial
        self.finais = set(finais)
        if rotulos is None:
            rotulos = {f: "ACEITA" for f in self.finais}
        self.rotulos = dict(rotulos)
        self._validar()

    # ------------------------------------------------------------------
    # Validação e construção
    # ------------------------------------------------------------------
    def _validar(self):
        conj = set(self.estados)
        if self.inicial not in conj:
            raise ValueError(f"Estado inicial '{self.inicial}' não pertence a Q.")
        if not self.finais <= conj:
            raise ValueError("Há estados finais que não pertencem a Q.")
        for (s, a), t in self.delta.items():
            if s not in conj or t not in conj:
                raise ValueError(f"Transição inválida: δ({s}, {a}) = {t}")
            if a not in self.alfabeto:
                raise ValueError(f"Símbolo '{a}' não pertence ao alfabeto.")
        for f in self.finais:
            self.rotulos.setdefault(f, "ACEITA")

    @classmethod
    def de_dict(cls, d):
        """Cria um AFD a partir de um dicionário (formato do arquivo JSON)."""
        delta = {}
        for s, trans in d["transicoes"].items():
            for a, t in trans.items():
                delta[(s, a)] = t
        return cls(d["estados"], d["alfabeto"], delta, d["inicial"], d["finais"])

    @classmethod
    def de_json(cls, caminho):
        with open(caminho, encoding="utf-8") as f:
            return cls.de_dict(json.load(f))

    # ------------------------------------------------------------------
    # Simulação
    # ------------------------------------------------------------------
    def executar(self, palavra):
        """Executa o AFD sobre a palavra. Retorna (aceita, caminho_de_estados)."""
        estado = self.inicial
        caminho = [estado]
        for simbolo in palavra:
            estado = self.delta.get((estado, simbolo))
            if estado is None:
                return False, caminho  # transição indefinida => rejeita
            caminho.append(estado)
        return estado in self.finais, caminho

    def aceita(self, palavra):
        return self.executar(palavra)[0]

    # ------------------------------------------------------------------
    # Passo 1: eliminação de estados inalcançáveis
    # ------------------------------------------------------------------
    def alcancaveis(self):
        """Conjunto de estados alcançáveis a partir do inicial (busca em largura)."""
        vistos = {self.inicial}
        fila = deque([self.inicial])
        while fila:
            s = fila.popleft()
            for a in self.alfabeto:
                t = self.delta.get((s, a))
                if t is not None and t not in vistos:
                    vistos.add(t)
                    fila.append(t)
        return vistos

    def _restrito_a(self, manter):
        """Cria um novo AFD contendo apenas os estados em `manter`."""
        estados = [s for s in self.estados if s in manter]
        delta = {(s, a): t for (s, a), t in self.delta.items()
                 if s in manter and t in manter}
        finais = self.finais & manter
        rotulos = {f: self.rotulos[f] for f in finais}
        return AFD(estados, self.alfabeto, delta, self.inicial, finais, rotulos)

    def remover_inalcancaveis(self):
        return self._restrito_a(self.alcancaveis())

    # ------------------------------------------------------------------
    # Estados inúteis (mortos): não conseguem chegar a nenhum estado final
    # ------------------------------------------------------------------
    def coalcancaveis(self):
        """Estados a partir dos quais é possível chegar a algum estado final."""
        reverso = {}
        for (s, a), t in self.delta.items():
            reverso.setdefault(t, set()).add(s)
        vistos = set(self.finais)
        fila = deque(self.finais)
        while fila:
            t = fila.popleft()
            for s in reverso.get(t, ()):
                if s not in vistos:
                    vistos.add(s)
                    fila.append(s)
        return vistos

    def remover_inuteis(self):
        """Remove estados mortos (o estado inicial é sempre preservado)."""
        return self._restrito_a(self.coalcancaveis() | {self.inicial})

    # ------------------------------------------------------------------
    # Completar o AFD (δ total) com um estado de erro
    # ------------------------------------------------------------------
    def completar(self, alfabeto=None):
        """Retorna AFD completo, opcionalmente sobre um alfabeto maior."""
        alf = sorted(set(self.alfabeto) | set(alfabeto or []))
        estados = list(self.estados)
        delta = dict(self.delta)
        faltando = [(s, a) for s in estados for a in alf if (s, a) not in delta]
        if faltando:
            morto = "∅"
            while morto in estados:
                morto += "'"
            estados.append(morto)
            for s, a in faltando:
                delta[(s, a)] = morto
            for a in alf:
                delta[(morto, a)] = morto
        return AFD(estados, alf, delta, self.inicial, self.finais, self.rotulos)

    # ------------------------------------------------------------------
    # Renomeação canônica (q0, q1, ...) em ordem de busca em largura
    # ------------------------------------------------------------------
    def renomeado(self, prefixo="q"):
        """Retorna (novo_afd, mapa_antigo->novo)."""
        ordem, vistos = [], {self.inicial}
        fila = deque([self.inicial])
        while fila:
            s = fila.popleft()
            ordem.append(s)
            for a in self.alfabeto:
                t = self.delta.get((s, a))
                if t is not None and t not in vistos:
                    vistos.add(t)
                    fila.append(t)
        ordem += [s for s in self.estados if s not in vistos]
        nome = {s: f"{prefixo}{i}" for i, s in enumerate(ordem)}
        novo = AFD(
            [nome[s] for s in ordem], self.alfabeto,
            {(nome[s], a): nome[t] for (s, a), t in self.delta.items()},
            nome[self.inicial],
            {nome[f] for f in self.finais},
            {nome[f]: r for f, r in self.rotulos.items() if f in self.finais},
        )
        return novo, nome

    # ------------------------------------------------------------------
    # Passo 2: eliminação de estados equivalentes (Moore) => AFD mínimo
    # ------------------------------------------------------------------
    @staticmethod
    def _particao_str(estados, bloco):
        grupos = {}
        for s in estados:
            grupos.setdefault(bloco[s], []).append(str(s))
        return " ".join("{" + ",".join(g) + "}" for g in grupos.values())

    def minimizar(self, manter_morto=False):
        """
        Gera o AFD mínimo.

        Etapas:
          1. remove estados inalcançáveis;
          2. completa o AFD (estado de erro), exigência do algoritmo;
          3. refina a partição de estados até estabilizar (Moore):
             partição inicial = {estados por rótulo final / não-final};
             dois estados ficam no mesmo bloco enquanto, para todo símbolo,
             suas transições levam a blocos iguais;
          4. cada bloco vira um estado do AFD mínimo;
          5. (opcional) remove o estado morto, deixando o AFD parcial.

        Retorna (afd_minimo, relatorio).
        """
        rel = {"estados_originais": len(self.estados)}

        # Etapa 1
        a1 = self.remover_inalcancaveis()
        rel["inalcancaveis"] = [str(s) for s in self.estados if s not in set(a1.estados)]

        # Etapa 2
        a2 = a1.completar()
        rel["morto_adicionado"] = len(a2.estados) > len(a1.estados)

        # Etapa 3: refinamento de partições
        ids = {}
        bloco = {}
        for s in a2.estados:
            chave = a2.rotulos[s] if s in a2.finais else None
            bloco[s] = ids.setdefault(chave, len(ids))
        passos = [self._particao_str(a2.estados, bloco)]
        while True:
            assinatura = {
                s: (bloco[s],) + tuple(bloco[a2.delta[(s, a)]] for a in a2.alfabeto)
                for s in a2.estados
            }
            ids2, novo = {}, {}
            for s in a2.estados:
                novo[s] = ids2.setdefault(assinatura[s], len(ids2))
            if len(ids2) == len(set(bloco.values())):
                break  # nenhuma divisão nova: partição estável
            bloco = novo
            passos.append(self._particao_str(a2.estados, bloco))
        rel["passos"] = passos

        # Etapa 4: construir o autômato quociente
        membros = {}
        for s in a2.estados:
            membros.setdefault(bloco[s], []).append(s)
        delta, finais, rotulos = {}, set(), {}
        for b, mem in membros.items():
            rep = mem[0]
            for a in a2.alfabeto:
                delta[(b, a)] = bloco[a2.delta[(rep, a)]]
            if rep in a2.finais:
                finais.add(b)
                rotulos[b] = a2.rotulos[rep]
        minimo = AFD(list(membros), a2.alfabeto, delta, bloco[a2.inicial], finais, rotulos)

        # Etapa 5: remover o estado morto
        removidos = []
        if not manter_morto:
            sem_mortos = minimo.remover_inuteis()
            removidos = [b for b in minimo.estados if b not in set(sem_mortos.estados)]
            minimo = sem_mortos
        rel["mortos_removidos"] = [[str(s) for s in membros[b]] for b in removidos]

        minimo, nome = minimo.renomeado()
        rel["classes"] = {nome[b]: [str(s) for s in membros[b]]
                          for b in nome}
        rel["estados_minimo"] = len(minimo.estados)
        return minimo, rel

    # ------------------------------------------------------------------
    # Verificação cruzada: algoritmo da tabela de pares marcados
    # ------------------------------------------------------------------
    def pares_equivalentes(self):
        """Conjunto de pares {p, q} de estados equivalentes (table-filling)."""
        a = self.remover_inalcancaveis().completar()

        def rot(s):
            return a.rotulos[s] if s in a.finais else None

        pares = [frozenset(p) for p in combinations(a.estados, 2)]
        marcados = {p for p in pares if rot(tuple(p)[0]) != rot(tuple(p)[1])}
        mudou = True
        while mudou:
            mudou = False
            for p in pares:
                if p in marcados:
                    continue
                s, t = tuple(p)
                for sim in a.alfabeto:
                    q = frozenset((a.delta[(s, sim)], a.delta[(t, sim)]))
                    if len(q) == 2 and q in marcados:
                        marcados.add(p)
                        mudou = True
                        break
        return {p for p in pares if p not in marcados}

    # ------------------------------------------------------------------
    # Equivalência de linguagens entre dois AFDs
    # ------------------------------------------------------------------
    def equivalente_a(self, outro):
        """True se os dois AFDs reconhecem a mesma linguagem (com os mesmos rótulos)."""
        alf = set(self.alfabeto) | set(outro.alfabeto)
        a, b = self.completar(alf), outro.completar(alf)

        def rot(x, s):
            return x.rotulos[s] if s in x.finais else None

        inicio = (a.inicial, b.inicial)
        vistos, fila = {inicio}, deque([inicio])
        while fila:
            s, t = fila.popleft()
            if rot(a, s) != rot(b, t):
                return False
            for sim in sorted(alf):
                par = (a.delta[(s, sim)], b.delta[(t, sim)])
                if par not in vistos:
                    vistos.add(par)
                    fila.append(par)
        return True

    # ------------------------------------------------------------------
    # Exibição
    # ------------------------------------------------------------------
    def tabela_texto(self):
        """Tabela de transição em texto. '->' = inicial, '*' = final."""
        largura = max([len(str(s)) for s in self.estados] + [5]) + 4
        cab = " " * 4 + "Estado".ljust(largura) + "".join(str(a).ljust(largura) for a in self.alfabeto)
        linhas = [cab, "-" * len(cab)]
        for s in self.estados:
            marca = ("->" if s == self.inicial else "  ") + ("*" if s in self.finais else " ")
            col = "".join(str(self.delta.get((s, a), "-")).ljust(largura) for a in self.alfabeto)
            linhas.append(f"{marca} " + str(s).ljust(largura) + col)
        return "\n".join(linhas)

    def para_dot(self, titulo="AFD"):
        """Código Graphviz (.dot). Visualize com `dot -Tpng arq.dot -o arq.png`."""
        def esc(x):
            return str(x).replace('"', '\\"')

        linhas = [f'digraph "{esc(titulo)}" {{', "  rankdir=LR;", '  node [shape=circle];',
                  '  __ini [shape=point];']
        for s in self.estados:
            forma = "doublecircle" if s in self.finais else "circle"
            texto = esc(s)
            if s in self.finais and self.rotulos[s] != "ACEITA":
                texto += "\\n" + esc(self.rotulos[s])  # quebra de linha do Graphviz
            linhas.append(f'  "{esc(s)}" [shape={forma}, label="{texto}"];')
        linhas.append(f'  __ini -> "{esc(self.inicial)}";')
        arestas = {}
        for (s, a), t in self.delta.items():
            arestas.setdefault((s, t), []).append(a)
        for (s, t), simbolos in arestas.items():
            rotulo = ",".join(sorted(simbolos)) if len(simbolos) <= 6 else f"{len(simbolos)} símbolos"
            linhas.append(f'  "{esc(s)}" -> "{esc(t)}" [label="{esc(rotulo)}"];')
        linhas.append("}")
        return "\n".join(linhas)
