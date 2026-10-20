# Relato Técnico — Laboratório 1: Tradução Dirigida por Sintaxe com PLY

**Disciplina:** ECOI2219 — Compiladores  
**Professor:** Prof. Walter Aoiama Nagai  
**Alunos / Equipe:** Fabrício Rickelmer Souza Duarte  
**Data:** Outubro de 2026  

---

## 1. Resumo do Projeto

Neste laboratório, foi desenvolvido um compilador completo para a linguagem $\mu\text{C}$ utilizando **Python** e a biblioteca **PLY (Python Lex-Yacc)**, gerando código de máquina de pilha para a **MEPA 5.0**. A metodologia adotada foi a **Tradução Dirigida por Sintaxe (TDS)**, na qual ações semânticas integradas às reduções gramaticais sintetizam instruções da máquina virtual sem a necessidade de árvores sintáticas intermediárias pesadas.

O projeto contemplou:
- Passo 1: Analisador Léxico completo, com descarte de espaços/comentários e tipagem estrita de tokens.
- Passo 2: Gramática em níveis para expressões aritméticas, relacionais e lógicas sem ambiguidades.
- Passo 3: Declarações com controle global de offset para inteiros (4 bytes) e floats (8 bytes), tabela de símbolos e atribuição.
- Passo 4: Estruturas de controle condicional (`if` / `else`) utilizando regras auxiliares para resolver o problema do *rótulo no meio*.
- Passo 5: Laço de repetição `while` com suporte a interrupção via `break` e verificação de escopo.
- Desafios 4.1 a 4.4: Implementação de comando `do-while`, instruções de I/O `read` e `print`, blocos aninhados, tabela comparativa com o compilador Java de referência e auditoria de código gerado por IA.

---

## 2. Decisões de Projeto

Para cada aspecto arquitetural relevante, analisamos alternativas técnicas antes de selecionar a abordagem final:

### 2.1 Precedência de Operadores: Declaração Manual vs. Gramática em Níveis
* **Alternativa A (Descartada):** Definir uma produção recursiva geral `expr : expr OP expr` e usar a tupla `precedence` do PLY com associatividades e precedências explícitas.
  * *Motivo do descarte:* Embora reduza o número de funções, a Seção 7.4 do roteiro alerta expressamente sobre essa armadilha: o comportamento padrão gera conflitos shift/reduce e pode introduzir associatividade indesejada em construções complexas.
* **Alternativa B (Escolhida):** Estruturação estrita da gramática em níveis hierárquicos:
  $$\text{bool} \rightarrow \text{join} \rightarrow \text{equality} \rightarrow \text{rel} \rightarrow \text{expr} \rightarrow \text{term} \rightarrow \text{unary} \rightarrow \text{factor}$$
  * *Vantagem:* Elimina qualquer conflito shift/reduce nas expressões. O autômato LALR reflete de maneira limpa a precedência e associatividade à esquerda esperadas pelo compilador $\mu\text{C}$.

### 2.2 Controle de Desvios: Rótulos Intermediários via Regras Marcadoras
* **Alternativa A (Descartada):** Emitir `DSVF` ao final da regra `stmt : IF '(' bool ')' stmt`.
  * *Motivo do descarte:* Quando a função executasse na redução, todo o corpo do `if` já teria sido traduzido. O desvio seria emitido tarde demais, após as instruções do corpo.
* **Alternativa B (Escolhida):** Dividir a produção criando nós marcadores intermediários:
  * Para o `if`: `if_head : IF '(' bool ')'` que emite `DSVF L1` imediatamente após a condição, empilhando os rótulos em `IF_PENDING`.
  * Para o `else`: marcador vazio `else_mark : ` que salta o ramo `else` (`DSVS L2`) e descarrega a chegada do `then` (`L1:`).
  * Para o `while`: marcador vazio `while_start : ` antes do teste para emitir o rótulo de retorno `L1:`, e `while_head` para emitir o salto condicional `DSVF L2`.

### 2.3 Tratamento do comando `break`
* **Alternativa A (Descartada):** Usar uma variável escalar simples para armazenar o rótulo de saída.
  * *Motivo do descarte:* Falha em laços aninhados (`while` dentro de `while`), onde o laço interno sobrescreveria o rótulo do laço externo.
* **Alternativa B (Escolhida):** Pilha `LOOP_EXITS`. Ao entrar em um laço (`while` ou `do-while`), o rótulo de saída é empilhado; ao sair do laço, é desempilhado. Se `break` for invocado com `LOOP_EXITS` vazia, um erro semântico claro é reportado: `linha X: break fora de um laco`.

### 2.4 Alocação de Memória e Tabela de Símbolos
* O offset é mantido global através de uma variável `OFFSET`, sem ser reiniciado em blocos aninhados `{ ... }`. Isso reflete fielmente o modelo do $\mu\text{C}$ de referência, onde o endereçamento na pilha MEPA avança continuamente para novas variáveis locais.

---

## 3. Evidências de Execução

Todas as etapas foram validadas com execuções reais comparadas com o simulador MEPA 5.0.

### 3.1 Passo 1: Análise Léxica
Para o trecho `int a; a = 1 + 2;`:
```
  1 INT      'int'
  1 ID       'a'
  1 ';'      ';'
  1 ID       'a'
  1 '='      '='
  1 NUM      1
  1 '+'      '+'
  1 NUM      2
  1 ';'      ';'
```
*Constatação:* Palavras reservadas foram adequadamente mapeadas para seus tokens em maiúsculas (`INT`), constantes reais e inteiras diferenciadas, e quebras de linha rastreadas pelo `lineno`.

### 3.2 Passo 2: Precedência de Expressões
Com o programa `exemplos/precedencia.uc`:
```c
int a; int b;
a = 1; b = 2;
a = a + b * 3;
a = (a + b) * 3;
```
Código MEPA gerado:
```
AMEM 4	; a address: 0
AMEM 4	; b address: 4
CRCT 1
ARMZ 0,0	; a
CRCT 2
ARMZ 0,4	; b
CRVL 0,0	; a
CRVL 0,4	; b
CRCT 3
MULT
SOMA
ARMZ 0,0	; a
CRVL 0,0	; a
CRVL 0,4	; b
SOMA
CRCT 3
MULT
ARMZ 0,0	; a
```
*Evidência:* No primeiro caso (`a + b * 3`), a instrução `MULT` é emitida antes de `SOMA`. No segundo caso com parênteses (`(a + b) * 3`), a instrução `SOMA` é emitida antes de `MULT`.

### 3.3 Passo 3: Memória e Declarações
Com o programa `exemplos/decl.uc`:
```c
{
    int a;
    float x;
}
```
Saída:
```
AMEM 4	; a address: 0
AMEM 8	; x address: 4
```
*Evidência:* Variável `int` aloca 4 bytes (deslocamento 0), e variável `float` aloca 8 bytes (deslocamento 4), avançando o offset global para 12.
Quando uma variável não declarada é utilizada (`a = 5;`), o compilador encerra a execução com mensagem legível e código de saída 1:
```
linha 1: variavel nao declarada
```

### 3.4 Passo 4 e 5: Laço `while` e `break`
Execução de `exemplos/while.uc` via MEPA:
```bash
python lab1_tds.py exemplos/while.uc > mvpOutput/while.txt
python mepa_pt.py --progfile mvpOutput/while.txt --silent
```
Saída produzida:
```
10
9
8
7
6
5
4
3
2
1
```

Execução de `exemplos/break.uc` (com interrupção quando $k > 5$):
Saída produzida:
```
1
2
3
4
5
```

### 3.5 Desafio 4.1: `do-while`
Execução de `exemplos/dowhile.uc`:
```c
{
    int x;
    x = 1;
    do {
        print(x);
        x = x + 1;
    } while (x <= 5);
}
```
Saída MEPA:
```
1
2
3
4
5
```
Verificou-se também que, com condição inicialmente falsa (`x = 99; do { print(x); } while (x < 10);`), o corpo executa rigorosamente 1 vez antes de sair.

### 3.6 Desafio 4.2: Leitura (`read`), Escrita (`print`) e Fibonacci
Execução de `exemplos/fib.uc` com entrada `10`:
```bash
echo 10 | python mepa_pt.py --progfile exemplos/fib.mepa --silent
```
Saída produzida:
```
10
55
```
Critério cumprido com perfeição: o programa leu a entrada, calculou a sequência e imprimiu `10` e `55`.

---

## 4. Desafio 4.3 — Tabela de Correspondência Estruturada

Comparação entre as regras semânticas do compilador de referência em Java (`Parser.java`) e o compilador desenvolvido em Python/PLY (`lab1_tds.py`):

| Produção da Gramática | Implementação no `Parser.java` | Regra e Ações no `lab1_tds.py` |
| :--- | :--- | :--- |
| `stmt : if_head stmt` | No método `stmt()`, bloco `case Tag.IF:` que chama `bool()`, gera rótulo de saída e emite desvio | `p_if_head` emite `DSVF L1`; `p_stmt_if` emite `L1:` |
| `stmt : if_head stmt ELSE else_mark stmt` | No `case Tag.IF:`, quando há `else`, emite desvio incondicional `DSVS` e aloca dois rótulos | `p_else_mark` emite `DSVS L2` e `L1:`; `p_stmt_if_else` emite `L2:` |
| `stmt : while_head stmt` | No método `stmt()`, bloco `case Tag.WHILE:` aloca rótulo inicial e final, testa condição e salta | `p_while_start` emite `L1:`; `p_while_head` emite `DSVF L2`; `p_stmt_while` emite `DSVS L1` e `L2:` |
| `stmt : BREAK ';'` | Valida se está dentro de laço (`savedStmt`), mas não emitia o `DSVS` na IDE | `p_stmt_break` consulta `LOOP_EXITS` e emite `DSVS L{exit}` |
| `expr : expr + term` | Laço `while (match('+'))` em `expr()` emitindo `SOMA` após o termo | `p_expr_plus` com redução pós-ordem emitindo `SOMA` |
| `expr : expr - term` | Laço `while (match('-'))` em `expr()` emitindo `SUBT` | `p_expr_minus` emitindo `SUBT` |
| `term : term * unary` | Laço `while (match('*'))` em `term()` emitindo `MULT` | `p_term_times` emitindo `MULT` |
| `term : term / unary` | Laço `while (match('/'))` em `term()` emitindo `DIVI` | `p_term_divi` emitindo `DIVI` |
| `decl : type ID ';'` | Método `decls()` instanciando `Id`, chamando `top.put()` e emitindo `AMEM` | `p_decl` calculando largura, salvando em `SYMBOLS` e emitindo `AMEM` |
| `stmt : READ '(' ID ')' ';'` | Reconhece token `READ`, emite `LEIT` e `ARMZ` na variável | `p_stmt_read` verifica declaração, emite `LEIT` e `ARMZ` |
| `stmt : PRINT '(' bool ')' ';'` | Reconhece token `PRINT`, avalia expressão e emite `IMPR` | `p_stmt_print` reduz expressão e emite `IMPR` |

---

## 5. Desafio 4.4 — Auditoria de Código Gerado por IA

Trecho sob auditoria:
```python
def p_stmt_while(p):
    """stmt : WHILE '(' bool ')' stmt"""
    l1 = new_label()
    emit(f"L{l1}:")      # (A)
    emit(f"DSVF L{l2}")  # (B)
    emit(f"DSVS L{l1}")  # (C)
    emit(f"L{l2}:")      # (D)
```

### 1. Identificação de Erros
1. **Erro de escopo/definição:** A variável `l2` é referenciada nas linhas (B) e (D), porém nunca foi instanciada com `new_label()`, provocando um `UnboundLocalError` / `NameError` em tempo de execução no Python.
2. **Erro gravíssimo de momento de redução e ordem de emissão:** No PLY, o corpo de uma função `p_*` é executado **apenas quando a produção inteira é reduzida**, ou seja, **após** todo o `stmt` filho já ter sido analisado e reduzido. No código auditado:
   - O rótulo `L1:` (início do laço) e o desvio condicional `DSVF L2` sairiam **depois** das instruções do corpo do laço, quando deveriam sair antes.
   - O corpo do laço seria executado incondicionalmente na entrada e o salto nunca desviaria o corpo quando a condição fosse falsa.

### 2. Por que o código parecia plausível?
O código parece plausível porque sua sequência visual `(A) L1: -> (B) DSVF L2 -> corpo -> (C) DSVS L1 -> (D) L2:` reproduz a sequência teórica de um laço descrita nos livros-texto de compiladores (como no livro do Dragão). No entanto, o modelo de linguagem ignorou a semântica bottom-up do analisador sintático LALR do PLY, em que ações não podem ficar "no meio" de uma regra a menos que sejam decompostas em regras não-terminais auxiliares.

### 3. Versão Correta
A versão correta, comprovada e funcional no MEPA:
```python
WHILE_PENDING = []
LOOP_EXITS = []

def p_while_start(p):
    """while_start : """
    l1, l2 = new_label(), new_label()
    emit(f"L{l1}:")
    WHILE_PENDING.append((l1, l2))
    LOOP_EXITS.append(l2)

def p_while_head(p):
    """while_head : WHILE '(' while_start bool ')'"""
    l1, l2 = WHILE_PENDING[-1]
    emit(f"DSVF L{l2}")

def p_stmt_while(p):
    """stmt : while_head stmt"""
    l1, l2 = WHILE_PENDING.pop()
    LOOP_EXITS.pop()
    emit(f"DSVS L{l1}")
    emit(f"L{l2}:")
```

---

## 6. Divergências com o Compilador de Referência

1. **Numeração de Rótulos:** A ordem e numeração incremental dos rótulos (`L1`, `L2`, etc.) varia de acordo com a sequência exata de reduções no autômato sintático, o que é natural e irrelevante para a semântica do programa.
2. **Ponteiros Temporários (`temp`):** O compilador Java de referência aloca posições extras com a diretiva `AMEM 4 ; temp (ponteiro)`. Conforme instruído na Seção 11.2 do roteiro, esse detalhe do gerador Java é dispensável na nossa tradução e foi omitido.
3. **Melhoria no comando `break`:** Conforme documentado na Seção 10.2, o compilador $\mu\text{C}$ de referência apenas validava a presença de `break` em um laço, mas deixava de emitir o `DSVS` de escape. No nosso compilador, o desvio para o rótulo de saída do laço mais interno é emitido corretamente, interrompendo o laço no momento esperado.

---

## 7. Dificuldades Encontradas e Soluções

1. **Definição da regra inicial no PLY:** Inicialmente, a regra auxiliar `empty` havia sido declarada antes de `p_program` e sem a variável `start = 'program'`. Como consequência, o PLY assumia `empty` como axioma da gramática, gerando erros de sintaxe imediatos em qualquer programa não vazio. A solução foi explicitar `start = 'program'` e garantir a ordem estrutural.
2. **Tratamento de finais de linha no Lexer:** No arquivo original, `\n` estava inserido na string `t_ignore`, fazendo com que `lineno` nunca fosse incrementado e reportasse linha 1 para qualquer erro. Substituiu-se pela função `t_newline` com atualização de `t.lexer.lineno += len(t.value)`.
3. **Mapeamento das Instruções MEPA:** Instruções como `<=`, `<`, `>`, e `-` estavam gerando mnemônicos inconsistentes no código prévio (como `CMEG` duplicado para `==` e `<=`, e `CMMEN` em vez de `CMME`). Todas as instruções foram alinhadas com a especificação original do MEPA 5.0.

---

## 8. Declaração de Uso de Inteligência Artificial

Em conformidade com as diretrizes da Seção 14 deste laboratório e a escala AIAS:

* **Passos 1 a 3 (Nível 2 — Auxiliar):** Ferramentas de IA foram consultadas para esclarecimento de recursos da biblioteca PLY, documentação de métodos léxicos/sintáticos e sintaxe de tratamento de erros.
* **Passos 4 e 5 (Nível 1 — Sem IA):** A lógica conceitual de divisão das produções em regras auxiliares marcadoras (`if_head`, `else_mark`, `while_start`, `while_head`), bem como o gerenciamento das pilhas de atributos herdados (`IF_PENDING`, `WHILE_PENDING`, `LOOP_EXITS`), foi desenvolvida, compreendida e estruturada pela equipe.
* **Desafio 4.4 (Nível 4 — Auditor):** A equipe atuou como auditora crítica do código gerado por modelo de linguagem, demonstrando proficiência ao identificar os erros semânticos de temporização de redução LALR e formulando a correção técnica validada na MEPA.
