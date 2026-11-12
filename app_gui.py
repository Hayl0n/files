import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from afd import AFD


class AppMinimizacaoAFD:
    def __init__(self, root):
        self.root = root
        self.root.title("Minimizador e Simulador de AFD - Linguagens Formais e Autômatos (UERN)")
        self.root.geometry("1000x700")
        self.root.minsize(900, 650)

        self.afd_atual = None
        self.afd_minimo = None
        self.entradas_transicoes = {}  # guarda os widgets da tabela de transição

        self._criar_layout()

    def _criar_layout(self):
        # Topo: Botões Globais de Ação
        frame_topo = ttk.Frame(self.root, padding=10)
        frame_topo.pack(fill=tk.X)

        btn_carregar = ttk.Button(frame_topo, text="📂 Carregar JSON", command=self.carregar_json)
        btn_carregar.pack(side=tk.LEFT, padx=5)

        btn_minimizar = ttk.Button(frame_topo, text="⚡ Minimizar AFD (Moore)", command=self.minimizar_afd)
        btn_minimizar.pack(side=tk.LEFT, padx=5)

        # Abas Principais
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # --- ABA 1: Formulario Passo a Passo ---
        self.aba_formulario = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.aba_formulario, text="✍️ Criar / Editar AFD")

        # Painel esquerdo (Campos bicos e definição)
        frame_form_esq = ttk.LabelFrame(self.aba_formulario, text=" 1. Definição do Autômato ", padding=10)
        frame_form_esq.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Passo 1: Alfabeto
        ttk.Label(frame_form_esq, text="Alfabeto (Σ) [separado por vírgula]:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(5, 2))
        self.txt_alfabeto = ttk.Entry(frame_form_esq)
        self.txt_alfabeto.insert(0, "a, b")
        self.txt_alfabeto.pack(fill=tk.X, pady=(0, 10))

        # Passo 2: Estados
        ttk.Label(frame_form_esq, text="Estados (Q) [separados por vírgula]:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(5, 2))
        self.txt_estados = ttk.Entry(frame_form_esq)
        self.txt_estados.insert(0, "q0, q1, q2, q3")
        self.txt_estados.pack(fill=tk.X, pady=(0, 10))

        btn_gerar_grade = ttk.Button(frame_form_esq, text="🔄 Gerar Tabela de Transições", command=self.gerar_grade_transicoes)
        btn_gerar_grade.pack(fill=tk.X, pady=5)

        # Passo 3: Estado Inicial
        ttk.Label(frame_form_esq, text="Estado Inicial (q0):", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(10, 2))
        self.combo_inicial = ttk.Combobox(frame_form_esq, state="readonly")
        self.combo_inicial.pack(fill=tk.X, pady=(0, 10))

        # Passo 4: Estados Finais
        ttk.Label(frame_form_esq, text="Estados Finais (F) [maroque os válidos]:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(5, 2))
        self.frame_finais = ttk.Frame(frame_form_esq)
        self.frame_finais.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.vars_finais = {}

        btn_salvar_afd = ttk.Button(frame_form_esq, text="✅ Construir / Salvar AFD", command=self.construir_afd_do_formulario)
        btn_salvar_afd.pack(fill=tk.X, pady=10)

        # Painel direito (Grade de Transições δ)
        frame_form_dir = ttk.LabelFrame(self.aba_formulario, text=" 2. Tabela de Transições δ(Estado, Símbolo) ", padding=10)
        frame_form_dir.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas_transicoes = tk.Canvas(frame_form_dir)
        self.scrollbar_trans = ttk.Scrollbar(frame_form_dir, orient="vertical", command=self.canvas_transicoes.yview)
        self.frame_grid_trans = ttk.Frame(self.canvas_transicoes)

        self.frame_grid_trans.bind("<Configure>", lambda e: self.canvas_transicoes.configure(scrollregion=self.canvas_transicoes.bbox("all")))
        self.canvas_transicoes.create_window((0, 0), window=self.frame_grid_trans, anchor="nw")
        self.canvas_transicoes.configure(yscrollcommand=self.scrollbar_trans.set)

        self.canvas_transicoes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar_trans.pack(side=tk.RIGHT, fill=tk.Y)

        # --- ABA 2: Tabelas Comparativas ---
        self.aba_tabelas = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.aba_tabelas, text="📊 Tabelas de Transição")

        frame_tabelas = ttk.PanedWindow(self.aba_tabelas, orient=tk.HORIZONTAL)
        frame_tabelas.pack(fill=tk.BOTH, expand=True)

        f_orig = ttk.LabelFrame(frame_tabelas, text=" AFD Original ", padding=5)
        self.txt_original = tk.Text(f_orig, font=("Consolas", 11), wrap=tk.NONE)
        self.txt_original.pack(fill=tk.BOTH, expand=True)
        frame_tabelas.add(f_orig, weight=1)

        f_min = ttk.LabelFrame(frame_tabelas, text=" AFD Mínimo ", padding=5)
        self.txt_minimo = tk.Text(f_min, font=("Consolas", 11), wrap=tk.NONE)
        self.txt_minimo.pack(fill=tk.BOTH, expand=True)
        frame_tabelas.add(f_min, weight=1)

        # --- ABA 3: Passos de Moore ---
        self.aba_moore = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.aba_moore, text="🔍 Passos da Minimização (Moore)")

        self.txt_relatorio = tk.Text(self.aba_moore, font=("Consolas", 11))
        self.txt_relatorio.pack(fill=tk.BOTH, expand=True)

        # --- ABA 4: Teste de Palavras ---
        self.aba_teste = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.aba_teste, text="▶ Simular Entrada")

        f_simular = ttk.Frame(self.aba_teste)
        f_simular.pack(fill=tk.X, pady=10)

        ttk.Label(f_simular, text="Digite a palavra para testar:").pack(side=tk.LEFT, padx=5)
        self.entry_palavra = ttk.Entry(f_simular, width=30)
        self.entry_palavra.pack(side=tk.LEFT, padx=5)

        btn_testar = ttk.Button(f_simular, text="Executar Simulação", command=self.testar_palavra)
        btn_testar.pack(side=tk.LEFT, padx=5)

        self.txt_resultado_sim = tk.Text(self.aba_teste, font=("Consolas", 11), height=15)
        self.txt_resultado_sim.pack(fill=tk.BOTH, expand=True, pady=5)

        # Gerar a grade inicial padrão
        self.gerar_grade_transicoes()

    def _obter_lista_estados(self):
        txt = self.txt_estados.get()
        return [e.strip() for e in txt.split(",") if e.strip()]

    def _obter_lista_alfabeto(self):
        txt = self.txt_alfabeto.get()
        return [a.strip() for a in txt.split(",") if a.strip()]

    def gerar_grade_transicoes(self):
        """Monta dinamicamente a grade de transições com base nos estados e símbolos."""
        # Limpa widgets antigos da grade
        for child in self.frame_grid_trans.winfo_children():
            child.destroy()

        estados = self._obter_lista_estados()
        alfabeto = self._obter_lista_alfabeto()

        if not estados or not alfabeto:
            messagebox.showwarning("Aviso", "Preencha os Estados e o Alfabeto primeiro.")
            return

        # Atualiza a lista do Estado Inicial
        self.combo_inicial['values'] = estados
        if estados:
            self.combo_inicial.current(0)

        # Atualiza as caixas dos Estados Finais
        for child in self.frame_finais.winfo_children():
            child.destroy()
        self.vars_finais = {}
        for est in estados:
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(self.frame_finais, text=est, variable=var)
            cb.pack(anchor=tk.W)
            self.vars_finais[est] = var

        # Cabeçalho da Grade de Transições
        ttk.Label(self.frame_grid_trans, text="Estado", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5, pady=5)
        for j, sim in enumerate(alfabeto):
            ttk.Label(self.frame_grid_trans, text=f"Símbolo '{sim}'", font=("Segoe UI", 9, "bold")).grid(row=0, column=j + 1, padx=5, pady=5)

        # Linhas da Grade (Estado x Símbolo)
        self.entradas_transicoes = {}
        opcoes_destino = ["(vazio / erro)"] + estados

        for i, est in enumerate(estados):
            ttk.Label(self.frame_grid_trans, text=f"{est} ➔", font=("Segoe UI", 9, "bold")).grid(row=i + 1, column=0, padx=5, pady=2)
            for j, sim in enumerate(alfabeto):
                cb_dest = ttk.Combobox(self.frame_grid_trans, values=opcoes_destino, width=12, state="readonly")
                cb_dest.current(0)  # Padrão é vazio
                cb_dest.grid(row=i + 1, column=j + 1, padx=5, pady=2)
                self.entradas_transicoes[(est, sim)] = cb_dest

    def construir_afd_do_formulario(self):
        """Lê os dados digitados na interface e monta a instância do AFD."""
        estados = self._obter_lista_estados()
        alfabeto = self._obter_lista_alfabeto()
        inicial = self.combo_inicial.get()
        finais = [est for est, var in self.vars_finais.items() if var.get()]

        if not inicial:
            messagebox .showerror("Erro", "Selecione o estado inicial.")
            return

        delta = {}
        for (est, sim), cb in self.entradas_transicoes.items():
            dest = cb.get()
            if dest and dest != "(vazio / erro)":
                delta[(est, sim)] = dest

        try:
            self.afd_atual = AFD(estados, alfabeto, delta, inicial, finais)
            self.afd_minimo = None

            # Exibe na aba de tabelas
            self.txt_original.delete("1.0", tk.END)
            self.txt_original.insert(tk.END, self.afd_atual.tabela_texto())

            self.txt_minimo.delete("1.0", tk.END)
            self.txt_relatorio.delete("1.0", tk.END)
            self.txt_resultado_sim.delete("1.0", tk.END)

            messagebox.showinfo("Sucesso", f"AFD construído com sucesso!\n{len(estados)} estados, {len(finais)} final(is).")
            self.notebook.select(self.aba_tabelas)
        except Exception as e:
            messagebox.showerror("Erro de Validação", f"Erro ao criar o AFD:\n{e}")

    def carregar_json(self):
        caminho = filedialog.askopenfilename(
            title="Selecione um arquivo de AFD",
            filetypes=[("Arquivos JSON", "*.json"), ("Todos os arquivos", "*.*")]
        )
        if not caminho:
            return

        try:
            self.afd_atual = AFD.de_json(caminho)
            self.afd_minimo = None

            self.txt_original.delete("1.0", tk.END)
            self.txt_original.insert(tk.END, self.afd_atual.tabela_texto())
            self.txt_minimo.delete("1.0", tk.END)
            self.txt_relatorio.delete("1.0", tk.END)

            messagebox.showinfo("Sucesso", "AFD carregado do JSON com sucesso!")
            self.notebook.select(self.aba_tabelas)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao carregar JSON:\n{e}")

    def minimizar_afd(self):
        if not self.afd_atual:
            messagebox.showwarning("Atenção", "Construa ou carregue um AFD primeiro!")
            return

        self.afd_minimo, rel = self.afd_atual.minimizar()

        self.txt_minimo.delete("1.0", tk.END)
        self.txt_minimo.insert(tk.END, self.afd_minimo.tabela_texto())

        self.txt_relatorio.delete("1.0", tk.END)
        self.txt_relatorio.insert(tk.END, "=== RELATÓRIO DE MINIMIZAÇÃO (ALGORITMO DE MOORE) ===\n\n")
        self.txt_relatorio.insert(tk.END, f"Estados originais: {rel['estados_originais']}\n")
        self.txt_relatorio.insert(tk.END, f"Inalcançáveis removidos: {rel['inalcancaveis']}\n")
        self.txt_relatorio.insert(tk.END, f"Estado morto adicionado: {rel['morto_adicionado']}\n\n")

        self.txt_relatorio.insert(tk.END, "--- Refinamento de Partições (Passo a Passo) ---\n")
        for i, passo in enumerate(rel["passos"]):
            self.txt_relatorio.insert(tk.END, f" P{i}: {passo}\n")

        self.txt_relatorio.insert(tk.END, f"\nClasses de Equivalência Finais:\n")
        for k, v in rel["classes"].items():
            self.txt_relatorio.insert(tk.END, f"  {k} = {v}\n")

        self.txt_relatorio.insert(tk.END, f"\nTotal de estados no AFD Mínimo: {rel['estados_minimo']}\n")
        self.notebook.select(self.aba_moore)

    def testar_palavra(self):
        if not self.afd_atual:
            messagebox.showwarning("Atenção", "Construa ou carregue um AFD primeiro!")
            return

        palavra = self.entry_palavra.get().strip()
        aceita_orig, caminho_orig = self.afd_atual.executar(palavra)

        saida = f"Palavra testada: '{palavra}'\n\n"
        saida += f"--- Teste no AFD Original ---\n"
        saida += f"Resultado: {'ACEITA ✅' if aceita_orig else 'REJEITADA ❌'}\n"
        saida += f"Caminho: {' -> '.join(map(str, caminho_orig))}\n\n"

        if self.afd_minimo:
            aceita_min, caminho_min = self.afd_minimo.executar(palavra)
            saida += f"--- Teste no AFD Mínimo ---\n"
            saida += f"Resultado: {'ACEITA ✅' if aceita_min else 'REJEITADA ❌'}\n"
            saida += f"Caminho: {' -> '.join(map(str, caminho_min))}\n"

        self.txt_resultado_sim.delete("1.0", tk.END)
        self.txt_resultado_sim.insert(tk.END, saida)


if __name__ == "__main__":
    root = tk.Tk()
    app = AppMinimizacaoAFD(root)
    root.mainloop()