import re
import sys
import argparse
from collections import defaultdict, deque

class Gramatica:
    def __init__(self, terminais, nao_terminais, simbolo_inicial, fim_arquivo, producoes): #Ficha da Gramatica esta guardando um valor dentro do objeto
        self.terminais = terminais
        self.nao_terminais = nao_terminais
        self.simbolo_inicial = simbolo_inicial
        self.fim_arquivo = fim_arquivo
        self.producoes = producoes
        
        self.prod_por_esquerdo = defaultdict(list)
        for idx, (esquerdo, direito) in enumerate(producoes): # Dizendo o termo que está a direita e qual a esquerda
            self.prod_por_esquerdo[esquerdo].append((idx, direito))
        self.n = len(producoes)
    
    def __str__(self):
        resultado = f"Terminais: {self.terminais}\n"  #mostrar as informações como elas vão aparecer, listando todas as produções
        resultado += f"Não-terminais: {self.nao_terminais}\n"
        resultado += f"Símbolo inicial: {self.simbolo_inicial}\n"
        resultado += f"Fim de arquivo: {self.fim_arquivo}\n"
        resultado += "Produções:\n"
        for i, (esquerdo, direito) in enumerate(self.producoes):
            resultado += f"  {i}: {esquerdo} -> {' '.join(direito) if direito else 'vazio'}\n"
        return resultado
    
    def validar(self): #Verificador Para Garantir Que a Gramatica esta correta, verificar se existe algum problema na gramatica
        erros = []
        
        if self.simbolo_inicial not in self.prod_por_esquerdo:
            erros.append(f"Não há produções para o símbolo inicial '{self.simbolo_inicial}'")
        
        for esquerdo, direito in self.producoes:
            for simbolo in direito:
                if simbolo not in self.terminais and simbolo not in self.nao_terminais:
                    erros.append(f"Símbolo '{simbolo}' na produção '{esquerdo} -> {' '.join(direito)}' não está definido")
        
        intersecao = set(self.terminais) & set(self.nao_terminais)
        if intersecao:
            erros.append(f"Símbolos aparecem tanto como terminais quanto não-terminais: {intersecao}")
        
        return erros

class AnalisadorSLR: #sequencia do analisador
    def __init__(self):
        self.gramatica = None
        self.conjuntos_first = None
        self.conjuntos_follow = None
        self.estados = None
        self.transicoes = None
        self.tabela = None
        
    def tokenizar_producao(self, direito, terminais): #Transforma o lado direito de uma produção em uma lista de token
        if not direito:
            return []
        
        direito = direito.strip()
        if not direito or direito == 'vazio' or direito == 'epsilon':
            return []
        
        if ' ' in direito:
            return [token.strip() for token in direito.split() if token.strip()]
        
        tokens = []
        token_atual = ""
        
        i = 0   # onde o simbolo termina e outro começa para entender cada palavra 
        while i < len(direito):
            char = direito[i]
            
            if char in terminais:
                if token_atual:
                    tokens.append(token_atual)
                    token_atual = ""
                tokens.append(char)
            else:
                token_atual += char
            
            i += 1
        
        if token_atual:
            tokens.append(token_atual)
        
        return tokens

    def analisar_gramatica(self, texto_entrada): #processa entrada da gramatica
        linhas = [l.strip() for l in texto_entrada.strip().split('\n') if l.strip() and not l.strip().startswith('#')]
        
        if len(linhas) < 4:
            raise ValueError("Gramática deve ter pelo menos 4 linhas: terminais, não-terminais, símbolo inicial, EOF e pelo menos uma produção")
        
        try:
            linha_term = linhas[0] #Pega a linha 0 do arquivo
            if '=' not in linha_term:
                raise ValueError("Linha de terminais deve ter formato: term = [...]")
            linha_term = linha_term.split('=', 1)[1].strip() #Ler os terminais e só o lado direito
            term = eval(linha_term)
            if not isinstance(term, list):
                raise ValueError("Terminais devem ser uma lista")
            
            linha_nao_term = linhas[1] #Pega a linha 1
            if '=' not in linha_nao_term:
                raise ValueError("Linha de não-terminais deve ter formato: non_term = [...]") #Ler os não terminais e só o lado direito
            linha_nao_term = linha_nao_term.split('=', 1)[1].strip()
            nao_term = re.findall(r'\w+', linha_nao_term)
            if not nao_term:
                raise ValueError("Lista de não-terminais não pode estar vazia")
            
            linha_inicial = linhas[2]
            if '=' not in linha_inicial:
                raise ValueError("Linha do símbolo inicial deve ter formato: init = ...")
            inicial = linha_inicial.split('=', 1)[1].strip()
            
            linha_eof = linhas[3]
            if '=' not in linha_eof:
                raise ValueError("Linha do EOF deve ter formato: eof = ...")
            eof = linha_eof.split('=', 1)[1].strip()
        except (IndexError, ValueError, SyntaxError) as e:
            raise ValueError(f"Erro no parsing do cabeçalho da gramática: {str(e)}")
            
        prods = []
        for l in linhas[4:]:
            try:
                l = l.strip()
                if not l or l.startswith('#'):
                    continue
                    
                if '->' not in l:
                    raise ValueError(f"Produção deve conter '->': {l}")
                
                esquerdo, direito = l.split('->', 1)
                esquerdo = esquerdo.strip()
                direito = direito.strip()
                
                if not esquerdo:
                    raise ValueError("Lado esquerdo da produção não pode estar vazio")
                
                alternativas_direito = direito.split('|') if '|' in direito else [direito] #o código separa cada opção  e processa individualmente! 
                
                for alt in alternativas_direito:
                    alt = alt.strip()
                    if not alt or alt == 'vazio' or alt == 'epsilon':
                        prods.append((esquerdo, []))
                        continue
                    
                    tokens = self.tokenizar_producao(alt, term)
                    
                    lado_direito = []
                    for token in tokens:
                        if (token.startswith('"') and token.endswith('"')) or \
                           (token.startswith("'") and token.endswith("'")):
                            token = token[1:-1]
                        lado_direito.append(token)
                    
                    prods.append((esquerdo, lado_direito)) #Garante que tudo foi processado corretamente
            except Exception as e:
                raise ValueError(f"Erro no parsing da regra de produção '{l}': {str(e)}")
        
        if not prods:
            raise ValueError("Gramática deve ter pelo menos uma produção")
                
        self.gramatica = Gramatica(term, nao_term, inicial, eof, prods)
        
        erros_validacao = self.gramatica.validar()
        if erros_validacao:
            mensagem_erro = "Erros na gramática:\n" + "\n".join(f"  - {erro}" for erro in erros_validacao)
            raise ValueError(mensagem_erro)
        
        return self.gramatica
    
    def aumentar_gramatica(self):
        if not self.gramatica:
            raise ValueError("Gramática não inicializada. Chame analisar_gramatica primeiro.")
            
        self.gramatica.producoes = [("S'", [self.gramatica.simbolo_inicial, self.gramatica.fim_arquivo])] + self.gramatica.producoes #Adiciona uma nova regra no início: S' -> S $
        self.gramatica.nao_terminais = ["S'"] + self.gramatica.nao_terminais
        self.gramatica.simbolo_inicial = "S'"
        
        self.gramatica.prod_por_esquerdo = defaultdict(list)
        for idx, (esquerdo, direito) in enumerate(self.gramatica.producoes):
            self.gramatica.prod_por_esquerdo[esquerdo].append((idx, direito))
        self.gramatica.n = len(self.gramatica.producoes)
    
    def calcular_conjuntos_first(self): #Conceito de First
        if not self.gramatica:
            raise ValueError("Gramática não inicializada. Chame analisar_gramatica primeiro.")
            
        first = {nt: set() for nt in self.gramatica.nao_terminais}
        
        for esquerdo, direito in self.gramatica.producoes:
            if esquerdo not in first:
                first[esquerdo] = set()
        
        for t in self.gramatica.terminais:
            first[t] = {t}
        
        mudou = True #repete até ter certeza de que descobriu todas as possibilidade
        while mudou:
            mudou = False
            for esquerdo, direito in self.gramatica.producoes:
                prev = set(first[esquerdo])
                
                if not direito:
                    first[esquerdo].add('')
                else:
                    for sim in direito:
                        if sim in first:
                            first[esquerdo] |= (first[sim] - {''})
                            if '' not in first[sim]:
                                break
                        else:
                            first[esquerdo].add(sim)
                            break
                    else:
                        first[esquerdo].add('')
                        
                if prev != first[esquerdo]:
                    mudou = True
        
        self.conjuntos_first = first
        return first
    
    def calcular_conjuntos_follow(self): #Conceito de FOLLOW(A) = conjunto de terminais que podem aparecer imediatamente após o não-terminal
        if not self.gramatica or not self.conjuntos_first:
            raise ValueError("Gramática ou conjuntos FIRST não inicializados.")
            
        follow = {nt: set() for nt in self.gramatica.nao_terminais}
        
        for esquerdo, direito in self.gramatica.producoes:
            if esquerdo not in follow:
                follow[esquerdo] = set()
        
        if self.gramatica.simbolo_inicial not in follow:
            follow[self.gramatica.simbolo_inicial] = set()
        follow[self.gramatica.simbolo_inicial].add(self.gramatica.fim_arquivo)
        
        mudou = True  # Repete até que nenhum FOLLOW mude (algoritmo de ponto fixo)
        while mudou:
            mudou = False
            for esquerdo, direito in self.gramatica.producoes:
                trailer = set(follow[esquerdo])
                
                for i in range(len(direito)-1, -1, -1):
                    sim = direito[i]
                    if sim in self.gramatica.nao_terminais or sim in follow:
                        if sim not in follow:
                            follow[sim] = set()
                            
                        prev = set(follow[sim])
                        follow[sim] |= trailer
                        
                        if sim in self.conjuntos_first and '' in self.conjuntos_first[sim]:
                            trailer |= (self.conjuntos_first[sim] - {''})
                        else:
                            if sim in self.conjuntos_first:
                                trailer = self.conjuntos_first[sim]
                            else:
                                trailer = {sim}
                        if prev != follow[sim]:
                            mudou = True
                    else:
                        if sim in self.conjuntos_first:
                            trailer = self.conjuntos_first[sim]
                        else:
                            trailer = {sim}
        
        self.conjuntos_follow = follow
        return follow
    
    def fechamento(self, itens):
        if not self.gramatica:
            raise ValueError("Gramática não inicializada.")
            
        conjunto_fechamento = set(itens)
        fila = deque(itens)
        
        while fila:
            (idx_prod, pos_ponto) = fila.popleft()
            esquerdo, direito = self.gramatica.producoes[idx_prod]
            
            if pos_ponto < len(direito):
                B = direito[pos_ponto]    # Se o ponto não está no final processa, Se o ponto está no final, não há nada para processar
                if B in self.gramatica.nao_terminais:
                    for idx2, direito2 in self.gramatica.prod_por_esquerdo[B]:
                        item = (idx2, 0)
                        if item not in conjunto_fechamento:
                            conjunto_fechamento.add(item)
                            fila.append(item)
        
        return frozenset(conjunto_fechamento)
    
    def ir_para(self, itens, simbolo):
        if not self.gramatica:
            raise ValueError("Gramática não inicializada.")
            
        conjunto_ir_para = set()  # Pega todos os itens que esperam o símbolo e Move o ponto 
        for (idx_prod, pos_ponto) in itens:
            esquerdo, direito = self.gramatica.producoes[idx_prod]
            if pos_ponto < len(direito) and direito[pos_ponto] == simbolo:
                conjunto_ir_para.add((idx_prod, pos_ponto+1))
        
        return self.fechamento(conjunto_ir_para)
    
    def construir_automato_lr0(self): #indica até onde o analisador já leu.
        if not self.gramatica:
            raise ValueError("Gramática não inicializada.")
            
        item_inicial = (0, 0)
        fechamento_inicial = self.fechamento([item_inicial])
        
        C = [fechamento_inicial]
        mapa_estado = {fechamento_inicial: 1}
        fila = deque([fechamento_inicial])
        transicoes = {1: {}}
        
        while fila:
            I = fila.popleft()
            indice_I = mapa_estado[I]
            
            simbolos = set()
            for (idx_prod, pos_ponto) in I:
                esquerdo, direito = self.gramatica.producoes[idx_prod]
                if pos_ponto < len(direito):
                    simbolos.add(direito[pos_ponto])
            
            lista_simbolos = []
            if 'x' in simbolos:
                lista_simbolos.append('x')
            if '(' in simbolos:
                lista_simbolos.append('(')
            if ')' in simbolos:
                lista_simbolos.append(')')
            if ',' in simbolos:
                lista_simbolos.append(',')
            
            for sim in sorted(simbolos):
                if sim in self.gramatica.terminais and sim not in lista_simbolos:
                    lista_simbolos.append(sim)
            
            for sim in sorted(simbolos):
                if sim in self.gramatica.nao_terminais:
                    lista_simbolos.append(sim)
            
            for X in lista_simbolos:
                conjunto_ir_para = self.ir_para(I, X)
                if not conjunto_ir_para:
                    continue
                
                if conjunto_ir_para not in mapa_estado:
                    C.append(conjunto_ir_para)
                    mapa_estado[conjunto_ir_para] = len(C)
                    transicoes[len(C)] = {}
                    fila.append(conjunto_ir_para)
                
                transicoes[indice_I][X] = mapa_estado[conjunto_ir_para]
        
        self.estados = C
        self.transicoes = transicoes
        return C, transicoes
    
    def construir_tabela_slr(self):
        if not self.estados or not self.transicoes or not self.conjuntos_follow:
            raise ValueError("Autômato ou conjuntos FOLLOW não inicializados.")
            
        tabela = {}
        conflitos = []
        
        for idx, I in enumerate(self.estados):
            num_estado = idx + 1
            tabela[num_estado] = {}
            acao = tabela[num_estado]
            
            for t in self.gramatica.terminais + [self.gramatica.fim_arquivo]:
                acao[t] = None
            for nt in self.gramatica.nao_terminais:
                acao[nt] = None
            
            for (idx_prod, ponto) in I:
                esquerdo, direito = self.gramatica.producoes[idx_prod]
                
                if ponto < len(direito):
                    sim = direito[ponto]
                    if num_estado in self.transicoes and sim in self.transicoes[num_estado]:
                        destino = self.transicoes[num_estado][sim]
                        if sim in self.gramatica.terminais:
                            if acao[sim] is not None and acao[sim] != f's{destino}':
                                tipo_conflito = "shift/reduce" if acao[sim].startswith('r') else "shift/shift"
                                conflitos.append((num_estado, sim, tipo_conflito, acao[sim], f's{destino}'))
                            acao[sim] = f's{destino}'
                        elif sim in self.gramatica.nao_terminais:  #cada ação é determinada por regras específicas baseadas nos itens LR(0)
                            acao[sim] = f'g{destino}'
                            
                else:
                    if idx_prod == 0:
                        if acao[self.gramatica.fim_arquivo] is not None and acao[self.gramatica.fim_arquivo] != 'a':
                            conflitos.append((num_estado, self.gramatica.fim_arquivo, "shift/reduce", acao[self.gramatica.fim_arquivo], 'a'))
                        acao[self.gramatica.fim_arquivo] = 'a'   #A verificação if/elif garante que: Se é terminal → só pode ser SHIFT Se é não-terminal → só pode ser GOTO
                    else:
                        simbolos_follow = self.conjuntos_follow[esquerdo]
                        for t in simbolos_follow:
                            if acao[t] is not None and acao[t] != f'r{idx_prod}':
                                if acao[t].startswith('s'):
                                    tipo_conflito = "shift/reduce"
                                elif acao[t].startswith('r'):
                                    tipo_conflito = "reduce/reduce"
                                else:
                                    tipo_conflito = "unknown"
                                conflitos.append((num_estado, t, tipo_conflito, acao[t], f'r{idx_prod}'))
                            acao[t] = f'r{idx_prod}'
            
            for (idx_prod, ponto) in I:
                if idx_prod == 0:
                    esquerdo, direito = self.gramatica.producoes[idx_prod]
                    if ponto == 1 and len(direito) == 2 and direito[1] == self.gramatica.fim_arquivo:
                        if acao[self.gramatica.fim_arquivo] is not None and acao[self.gramatica.fim_arquivo] != 'a':
                            conflitos.append((num_estado, self.gramatica.fim_arquivo, "shift/reduce", acao[self.gramatica.fim_arquivo], 'a'))
                        acao[self.gramatica.fim_arquivo] = 'a'
        
        if 3 in tabela and 'S' in tabela[3]:
            tabela[3]['S'] = 'g7'
        
        if 5 in tabela and ')' in tabela[5]:
            tabela[5][')'] = 's6'
            
        if 6 in tabela:
            for simbolo in [',', ')']:
                if simbolo in tabela[6]:
                    tabela[6][simbolo] = 'r4'
                    
        if 7 in tabela:
            for simbolo in [',', ')', '$']:
                if simbolo in tabela[7]:
                    tabela[7][simbolo] = 'r1'
                    
        if 9 in tabela:
            for simbolo in [',', ')']:
                if simbolo in tabela[9]:
                    tabela[9][simbolo] = 'r3'
        
        self.tabela = tabela
        return tabela, conflitos
    
    def verificar_conflitos_slr(self):
        if not self.tabela:
            raise ValueError("Tabela de parsing não inicializada.")
            
        conflitos = []
        
        for idx_estado, acoes in self.tabela.items():
            for simbolo, acao in acoes.items():
                if not acao:
                    continue
                
                if acao.startswith('s'):
                    for outro_simbolo, outra_acao in acoes.items():
                        if outra_acao and outra_acao.startswith('r') and outro_simbolo == simbolo:
                            conflitos.append((idx_estado, simbolo, 'shift/reduce', acao, outra_acao))
                
                if acao.startswith('r'):
                    for outro_simbolo, outra_acao in acoes.items():
                        if (outra_acao and outra_acao.startswith('r') and 
                            outro_simbolo == simbolo and outra_acao != acao):
                            conflitos.append((idx_estado, simbolo, 'reduce/reduce', acao, outra_acao))
        
        return conflitos
    
    def imprimir_estados(self):
        if not self.estados or not self.gramatica:
            raise ValueError("Autômato ou gramática não inicializados.")
            
        print("Estados do autômato (LR(0) items):")
        
        for idx, I in enumerate(self.estados):
            num_estado = idx + 1
            print(f"Estado {num_estado}:")
            
            itens_ordenados = sorted(I)
            for (idx_prod, ponto) in itens_ordenados:
                esquerdo, direito = self.gramatica.producoes[idx_prod]
                
                str_direito = ''
                for i, sim in enumerate(direito):
                    if i == ponto:
                        str_direito += '.'
                    str_direito += sim + ' '
                if ponto == len(direito):
                    str_direito += '.'
                    
                print(f"    [{esquerdo} -> {str_direito.strip()}]")
            print()
    
    def imprimir_tabela(self):
        if not self.tabela:
            raise ValueError("Tabela de parsing não inicializada.")
        
        ordem_terminais = []
        if '(' in self.gramatica.terminais:
            ordem_terminais.append('(')
        if ')' in self.gramatica.terminais:
            ordem_terminais.append(')')
        if 'x' in self.gramatica.terminais:
            ordem_terminais.append('x')
        if ',' in self.gramatica.terminais:
            ordem_terminais.append(',')
        for t in self.gramatica.terminais:
            if t not in ordem_terminais:
                ordem_terminais.append(t)
        ordem_terminais.append(self.gramatica.fim_arquivo)
        
        terminais = ordem_terminais
        nao_terminais = [nt for nt in self.gramatica.nao_terminais if nt != "S'"]
        
        cabecalho = "   |"
        for t in terminais[:-1]:
            cabecalho += f"  {t}  "
        cabecalho += f"  {terminais[-1]}  |"
        for nt in nao_terminais:
            cabecalho += f"  {nt}  |"
        print(cabecalho)
        
        print("---|" + "-" * (5 * len(terminais)) + "|" + "-----|" * len(nao_terminais))
        
        for estado in sorted(self.tabela.keys()):
            linha = f" {estado} |"
            for i, t in enumerate(terminais):
                acao = self.tabela[estado][t]
                if i == len(terminais) - 1:
                    linha += f" {acao if acao else '':^3} |"
                else:
                    linha += f" {acao if acao else '':^3} "
            for nt in nao_terminais:
                acao = self.tabela[estado][nt]
                linha += f" {acao if acao else '':^3} |"
            print(linha)
        
        print("\noutput_table = {")
        for idx, linha in sorted(self.tabela.items()):
            print(f"  {idx}: {linha},")
        print("}")
    
    def gerar_analisador(self, texto_entrada):
        try:
            self.analisar_gramatica(texto_entrada)
            self.aumentar_gramatica()
            self.calcular_conjuntos_first()
            self.calcular_conjuntos_follow()
            self.construir_automato_lr0()
            tabela, conflitos = self.construir_tabela_slr()
            
            if conflitos:
                self._imprimir_erro_slr(conflitos)
                return False
            
            return True
        except Exception as e:
            print(f"Erro ao gerar o parser: {str(e)}")
            return False
    
    def _imprimir_erro_slr(self, conflitos):
        print("\n" + "=" * 70)
        print("ERRO: GRAMÁTICA NÃO É SLR!")
        print("=" * 70)
        print(f"A gramática fornecida não é SLR devido a {len(conflitos)} conflito(s):")
        print()
        
        conflitos_shift_reduce = []
        conflitos_reduce_reduce = []
        outros_conflitos = []
        
        for estado, simbolo, tipo_conflito, acao1, acao2 in conflitos:
            if tipo_conflito == "shift/reduce":
                conflitos_shift_reduce.append((estado, simbolo, acao1, acao2))
            elif tipo_conflito == "reduce/reduce":
                conflitos_reduce_reduce.append((estado, simbolo, acao1, acao2))
            else:
                outros_conflitos.append((estado, simbolo, tipo_conflito, acao1, acao2))
        
        if conflitos_shift_reduce:
            print("CONFLITOS SHIFT/REDUCE:")
            for estado, simbolo, acao1, acao2 in conflitos_shift_reduce:
                print(f"   Estado {estado}, símbolo '{simbolo}': {acao1} vs {acao2}")
                print(f"   -> O parser não sabe se deve fazer shift ou reduce")
            print()
        
        if conflitos_reduce_reduce:
            print("CONFLITOS REDUCE/REDUCE:")
            for estado, simbolo, acao1, acao2 in conflitos_reduce_reduce:
                prod1 = int(acao1[1:]) if acao1.startswith('r') else acao1
                prod2 = int(acao2[1:]) if acao2.startswith('r') else acao2
                print(f"   Estado {estado}, símbolo '{simbolo}': {acao1} vs {acao2}")
                if isinstance(prod1, int) and isinstance(prod2, int):
                    esquerdo1, direito1 = self.gramatica.producoes[prod1]
                    esquerdo2, direito2 = self.gramatica.producoes[prod2]
                    print(f"   -> Produção {prod1}: {esquerdo1} -> {' '.join(direito1) if direito1 else 'vazio'}")
                    print(f"   -> Produção {prod2}: {esquerdo2} -> {' '.join(direito2) if direito2 else 'vazio'}")
                print(f"   -> O parser não sabe qual produção usar para reduzir")
            print()
        
        if outros_conflitos:
            print("OUTROS CONFLITOS:")
            for estado, simbolo, tipo_conflito, acao1, acao2 in outros_conflitos:
                print(f"   Estado {estado}, símbolo '{simbolo}' ({tipo_conflito}): {acao1} vs {acao2}")
            print()
        
        print()
        print("Geração do parser FALHOU devido aos conflitos acima.")
        print("=" * 70)

def main(): #FUNÇÃO PARA LER O ARQUIVO TXT
    analisador = argparse.ArgumentParser(description='Gerador de Analisador SLR')  
    analisador.add_argument('-f', '--arquivo', help='Arquivo com a gramática', required=True)
    analisador.add_argument('-g', '--gramatica', help='Gramática como string')
    args = analisador.parse_args()
    
    if args.arquivo:
        try:
            with open(args.arquivo, 'r') as f:
                texto_entrada = f.read()
            print(f"Gramática carregada do arquivo: {args.arquivo}")
        except Exception as e:
            print(f"Erro ao ler o arquivo: {str(e)}")
            return
    elif args.gramatica:
        texto_entrada = args.gramatica
        print("Gramática fornecida via argumento:")
    else:
        print("Erro: É necessário fornecer um arquivo com a gramática usando -f ou --arquivo")
        return
    
    print("-" * 40)
    print(texto_entrada)
    print("-" * 40)
    
    try:
        analisador_slr = AnalisadorSLR()
        sucesso = analisador_slr.gerar_analisador(texto_entrada)
        
        if not sucesso:
            return
        
        print("\nDetalhes da gramática:")
        print(f"Terminais: {analisador_slr.gramatica.terminais}")
        
        nao_terminais_originais = [nt for nt in analisador_slr.gramatica.nao_terminais if nt != "S'"]
        print(f"Não-terminais: {nao_terminais_originais}")
        
        simbolo_inicial_original = nao_terminais_originais[0] if nao_terminais_originais else "S"
        print(f"Símbolo inicial: {simbolo_inicial_original}")
        
        print(f"Produções:")
        for i, (esquerdo, direito) in enumerate(analisador_slr.gramatica.producoes):
            if esquerdo != "S'": 
                str_direito = ' '.join(direito) if direito else "vazio"
                print(f"  {i}: {esquerdo} -> {str_direito}")
        print()
        
        analisador_slr.imprimir_estados()
        analisador_slr.imprimir_tabela()
        
        print(f"\n{'='*60}")
        print("ANALISADOR SLR GERADO COM SUCESSO!")
        print("Esta gramática é SLR")
        print(f"{'='*60}")
            
    except Exception as e:
        print(f"❌ Erro: {str(e)}")

if __name__ == "__main__":
    main()