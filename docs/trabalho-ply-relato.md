# Relatório Técnico — Laboratório 1: Tradução Dirigida por Sintaxe com PLY

**Disciplina:** ECOI2219 — Compiladores  
**Professor:** Prof. Walter Aoiama Nagai  
**Equipe:** Fabrício Rickelmer Souza Duarte | Esther de Faria | Luiza Alves de Oliveira Vieira | Thamara Luiza Bicalho Oliveira Silva  
**Data:** Outubro de 2026  

## 1. Resumo do Projeto

Neste laboratório foi desenvolvido um compilador para a linguagem µC em **Python**, com a biblioteca **PLY (Python Lex-Yacc)**, gerando código de máquina de pilha para a **MEPA 5.0**. A metodologia foi a **Tradução Dirigida por Sintaxe (TDS)**: as ações semânticas acompanham as reduções gramaticais e emitem as instruções da máquina virtual, sem árvore sintática intermediária.

O projeto contemplou:
- Passo 1: analisador léxico com palavras reservadas e controle de linha (`lineno`).
- Passo 2: gramática em níveis (`bool → join → equality → rel → expr → term → unary → factor`) para expressões, sem ambiguidades.
- Passo 3: declarações com `OFFSET` global (`int` = 4 bytes, `float` = 8 bytes), tabela de símbolos e atribuição.
- Passo 4: comando condicional (`if` / `else`) com regras auxiliares para o problema do *rótulo no meio*.
- Passo 5: laço `while` com `break` e verificação de `break` fora de laço.
- Desafios 4.1 a 4.4: `do-while`, `read` e `print`, blocos aninhados, tabela comparativa com o compilador Java de referência e auditoria de código gerado por IA.

---

## 2. Decisões de Projeto

Para cada decisão relevante, registramos a alternativa descartada e o motivo.

### 2.1 Precedência de operadores: declaração manual x gramática em níveis
* **Alternativa descartada:** produção geral `expr : expr OP expr` com a tupla `precedence` do PLY. Reduziria o número de funções, mas a Seção 7.4 do roteiro alerta que essa forma é ambígua e gera conflitos *shift/reduce*, com associatividade indesejada.
* **Escolhida:** gramática estruturada em níveis hierárquicos, `bool → join → equality → rel → expr → term → unary → factor`.
* **Vantagem:** elimina os conflitos *shift/reduce* nas expressões e o autômato LALR reflete a precedência e a associatividade à esquerda do µC.

### 2.2 Controle de desvios: regras marcadoras
* **Alternativa descartada:** emitir `DSVF` ao final da regra `stmt : IF '(' bool ')' stmt`.
  * *Motivo:* quando a função roda, o corpo do `if` já foi traduzido; o desvio sairia tarde demais, depois das instruções do corpo.
* **Escolhida:** dividir a produção com marcadores intermediários:
  * `if`: `if_head : IF '(' bool ')'` emite `DSVF L1` logo após a condição e empilha os rótulos em `IF_PENDING`.
  * `else`: marcador vazio `else_mark` emite `DSVS L2` (pula o `else`) e `L1:` (chegada do `then`).
  * `while`: marcador vazio `while_start` emite o rótulo de retorno `L1:` antes do teste; `while_head` emite `DSVF L2`.
* *Por que `IF_PENDING` é uma pilha:* Decidimos usar a `IF_PENDING` como pilha para suportar comandos condicionais aninhados. Se fosse uma variável simples, ao traduzir um código como `if (a) if (b) print(1);`, os rótulos gerados para o `if (b)` sobrescreveriam e apagariam os do `if (a)`. Com a estrutura de pilha, os rótulos do `if` externo ficam salvos na base enquanto o interno empilha e resolve os seus no topo, garantindo que todos os desvios sejam fechados na ordem exata e sem perda de referência.

### 2.3 Tratamento do `break`
* **Alternativa descartada:** variável escalar com o rótulo de saída.
  * *Motivo:* falha em laços aninhados, porque o laço interno sobrescreveria o rótulo do externo.
* **Escolhida:** pilha `LOOP_EXITS`. O rótulo de saída é empilhado ao entrar no laço e desempilhado ao sair. Se `break` ocorrer com a pilha vazia, o compilador reporta `linha X: break fora de um laco`.

### 2.4 Alocação de memória e tabela de símbolos
* **Alternativa descartada:** reiniciar o `OFFSET` a cada `{`.
  * *Motivo:* o roteiro (Passo 3, "Armadilha") avisa que o programa compila mas lê a memória errada, porque o µC numera as variáveis numa sequência única mesmo com blocos aninhados.
* **Escolhida:** `OFFSET` global, nunca reiniciado em `{ ... }`.

### 2.5 Largura dos tipos
`int` ocupa 4 bytes e `float` 8 bytes (`symbols/Type.java`); por isso o `AMEM` e o incremento do `OFFSET` dependem do tipo declarado.

### 2.6 Variável não declarada
* **Alternativa descartada:** deixar o dicionário `SYMBOLS` lançar `KeyError`. Se não tratarmos isso, o compilador simplesmente "quebra" e fecha do nada com o erro nativo do Python. Para evitar esse crash, preferimos apontar o problema: o programa avisa em que linha o erro ocorreu (dizendo "variável não declarada") e encerra a execução de forma limpa e controlada, exatamente como a especificação pede.
* **Escolhida:** verificar na regra `factor : ID` e encerrar com `linha X: variavel nao declarada`.

### 2.7 Formato dos rótulos para o MEPA
* **Escolhida:** emitir o rótulo já na mesma linha da instrução (formato nativo do MEPA).
* **Alternativa descartada:** gerar o rótulo em uma linha separada e depender do comando `awk` para fazer a conversão depois.
* **Motivo:** gerar o código já formatado para o MEPA (ex.: `L1: SOMA`) deixou o compilador mais independente e prático. Descartamos o uso do `awk` porque exigir um passo extra de conversão no terminal só deixaria a execução e a automação da nossa bateria de testes mais burocrática e lenta.

---

## 3. Evidências de Execução

### 3.1 Suíte de testes
Comando executado na pasta do projeto (`ply-compiler`):

```
python tests/test_suite.py
```

Resultado (saída do terminal):

| Programa | Instruções emitidas | Saída do MEPA |
|---|---|---|
| `examples\expr.uc` | 7 | `[]` |
| `examples\decl.uc` | 4 | `[]` |
| `examples\precedencia.uc` | 20 | `[]` |
| `examples\if.uc` | 14 | `[]` |
| `examples\while.uc` | 18 | `[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]` |
| `examples\break.uc` | 24 | `[1, 2, 3, 4, 5]` |
| `examples\dowhile.uc` | 17 | `[1, 2, 3, 4, 5]` |
| `examples\fib.uc` | 38 | `[10, 55]` |

A suíte terminou com `=== TODOS OS TESTES FORAM CONCLUIDOS COM SUCESSO ===`. Em `expr`, `decl`, `precedencia` e `if`, a saída `[]` indica que os programas compilam e executam sem erro no MEPA, mas não imprimem valores; a verificação dos valores está nas subseções a seguir.

Saída completa do terminal:

```
> python tests/test_suite.py
=== EXECUTANDO BATERIA DE TESTES DO COMPILADOR ===

[TESTE] Compilando examples\expr.uc...
  Compilado com sucesso (7 instrucoes emitidas).
  Executando no MEPA (mepa\mepa_pt.py)...
  SUCESSO! Saida MEPA: []

[TESTE] Compilando examples\decl.uc...
  Compilado com sucesso (4 instrucoes emitidas).
  Executando no MEPA (mepa\mepa_pt.py)...
  SUCESSO! Saida MEPA: []

[TESTE] Compilando examples\precedencia.uc...
  Compilado com sucesso (20 instrucoes emitidas).
  Executando no MEPA (mepa\mepa_pt.py)...
  SUCESSO! Saida MEPA: []

[TESTE] Compilando examples\if.uc...
  Compilado com sucesso (14 instrucoes emitidas).
  Executando no MEPA (mepa\mepa_pt.py)...
  SUCESSO! Saida MEPA: []

[TESTE] Compilando examples\while.uc...
  Compilado com sucesso (18 instrucoes emitidas).
  Executando no MEPA (mepa\mepa_pt.py)...
  SUCESSO! Saida MEPA: [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

[TESTE] Compilando examples\break.uc...
  Compilado com sucesso (24 instrucoes emitidas).
  Executando no MEPA (mepa\mepa_pt.py)...
  SUCESSO! Saida MEPA: [1, 2, 3, 4, 5]

[TESTE] Compilando examples\dowhile.uc...
  Compilado com sucesso (17 instrucoes emitidas).
  Executando no MEPA (mepa\mepa_pt.py)...
  SUCESSO! Saida MEPA: [1, 2, 3, 4, 5]

[TESTE] Compilando examples\fib.uc...
  Compilado com sucesso (38 instrucoes emitidas).
  Executando no MEPA (mepa\mepa_pt.py)...
  SUCESSO! Saida MEPA: [10, 55]

=== TODOS OS TESTES FORAM CONCLUIDOS COM SUCESSO ===
```

### 3.2 Passo 1: análise léxica
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
*Constatação:* as palavras reservadas são mapeadas para tokens em maiúsculas (`INT`) e as quebras de linha são rastreadas por `lineno` (`t_newline`).

### 3.3 Passo 2: precedência de expressões
Com `examples/precedencia.uc`:
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
*Evidência:* em `a + b * 3`, o `MULT` é emitido antes do `SOMA`; em `(a + b) * 3`, o `SOMA` é emitido antes do `MULT`.

Valores no MEPA, com `examples/precedencia_print.uc` (imprime `a` após cada atribuição): saída obtida `[7, 27]`. Isso comprova que o compilador respeitou a precedência da multiplicação sobre a soma no primeiro caso (`1 + 2 * 3 = 7`) e a precedência dos parênteses no segundo (`(7 + 2) * 3 = 27`).

### 3.4 Passo 3: memória e declarações
Com `examples/decl.uc`:
```c
{
    int a;
    float x;
}
```
Código gerado:
```
AMEM 4	; a address: 0
AMEM 8	; x address: 4
```
*Evidência:* `int` aloca 4 bytes (deslocamento 0) e `float` 8 bytes (deslocamento 4), levando o `OFFSET` global a 12.

Uso de variável não declarada (`a = 5;`): o compilador encerra com mensagem legível e código de saída 1, sem falha do Python:
```
linha 1: variavel nao declarada
```
Atribuição `a = 1 + 2;` com `examples/expr_print.uc` (imprime `a` em seguida): saída obtida `[3]`.

### 3.5 Passo 4: `if` / `else`
O `examples/if.uc` da suíte compila (14 instruções) e executa sem erro no MEPA. Para provar os dois caminhos:

* `examples/if_else_pos.uc` (`a = 5`): saída obtida `[1]`
* `examples/if_else_neg.uc` (`a = -5`): saída obtida `[2]`
* `examples/if_aninhado.uc`: saída obtida `[1, 9]`

Isso mostra que os desvios executam os ramos corretos nos dois caminhos e que a pilha `IF_PENDING` gerenciou o aninhamento sem perder os rótulos do `if` externo.

Trecho do código gerado para `if.uc` (`if (a > 0) a = 1; else a = 2;`), mostrando o `DSVF` separando condição de corpo:
```
CRVL 0,0	; a
CRCT 0
CMMA             ← condição: a > 0
DSVF L1          ← desvia para o ramo else se falso
CRCT 1
ARMZ 0,0	; a  ← ramo then
DSVS L2          ← pula o ramo else
L1:
CRCT 2
ARMZ 0,0	; a  ← ramo else
L2:
```

### 3.6 Passo 5: `while` e `break`
Saídas da suíte (3.1): `while.uc` imprime `[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]` e `break.uc` (interrompe o laço quando `k > 5`) imprime `[1, 2, 3, 4, 5]`.

* `break` em laços aninhados (`examples/break_aninhado.uc` — laço externo `i=1..3`, laço interno `j=1..3` com `if (j > 1) break`): saída obtida `[11, 21, 31]`. O `break` interrompeu corretamente apenas o laço interno, deixando o externo continuar.
* `break` fora de laço (`examples/break_fora.uc` — `{ int k; break; }`): mensagem de erro obtida:
  ```
  linha 1: break fora de um laco
  ```
  O compilador encerrou com código de saída 1 sem falha do Python.

### 3.7 Desafio 4.1: `do-while`
`examples/dowhile.uc`:
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
Saída do MEPA (3.1): `[1, 2, 3, 4, 5]`.

Com condição inicialmente falsa (`examples/dowhile_falso.uc`, `x = 99`, `while (x < 10)`): saída obtida `[99]`. Como o teste lógico fica no final do laço, o corpo imprimiu o valor inicial 99 uma única vez antes de a condição (`x < 10`) ser avaliada como falsa e a execução terminar.

### 3.8 Desafio 4.2: `read`, `print` e Fibonacci
`examples/fib.uc` com entrada `10` produz `[10, 55]` na suíte (3.1), cumprindo o critério do enunciado.

A entrada `10` é fornecida ao MEPA via `stdin` pelo parâmetro `input` do `subprocess.run`, definido na lista `EXAMPLES` do `test_suite.py`:
```python
(os.path.join(EXAMPLES_DIR, "fib.uc"), "10\n"),
```
O valor `"10\n"` é passado como `input=input_data` ao chamar `mepa_pt.py --silent`, simulando o usuário digitando `10` e pressionando Enter.

---

## 4. Desafio 4.3 — Tabela de correspondência

Programa escolhido: `while.uc`, de `uc-full/examples/`.



| Produção | Implementação no `Parser.java` | Regra e ações no compilador PLY |
| :--- | :--- | :--- |
| `stmt : if_head stmt` | `stmt()`, `case Tag.IF:` — chama `bool()`, gera rótulo de saída e emite desvio | `p_if_head` emite `DSVF L1`; `p_stmt_if` emite `L1:` |
| `stmt : if_head stmt ELSE else_mark stmt` | `case Tag.IF:` com `else`: emite `DSVS` e aloca dois rótulos | `p_else_mark` emite `DSVS L2` e `L1:`; `p_stmt_if_else` emite `L2:` |
| `stmt : while_head stmt` | `stmt()`, `case Tag.WHILE:` — rótulos inicial e final, testa a condição e salta | `p_while_start` emite `L1:`; `p_while_head` emite `DSVF L2`; `p_stmt_while` emite `DSVS L1` e `L2:` |
| `stmt : BREAK ';'` | Valida se está dentro de laço, mas não emitia o `DSVS` na IDE | `p_stmt_break` consulta `LOOP_EXITS` e emite `DSVS L{exit}` |
| `expr : expr + term` | laço `while (match('+'))` em `expr()`, emite `SOMA` | `p_expr_plus` (pós-ordem) emite `SOMA` |
| `expr : expr - term` | laço `while (match('-'))` em `expr()`, emite `SUBT` | `p_expr_minus` emite `SUBT` |
| `term : term * unary` | laço `while (match('*'))` em `term()`, emite `MULT` | `p_term_times` emite `MULT` |
| `term : term / unary` | laço `while (match('/'))` em `term()`, emite `DIVI` | `p_term_divi` emite `DIVI` |
| `decl : type ID ';'` | `decls()`: instancia `Id`, `top.put()` e emite `AMEM` | `p_decl` calcula a largura, grava em `SYMBOLS` e emite `AMEM` |
| `stmt : READ '(' ID ')' ';'` | reconhece `READ`, emite `LEIT` e `ARMZ` | `p_stmt_read` verifica a declaração, emite `LEIT` e `ARMZ` |
| `stmt : PRINT '(' bool ')' ';'` | reconhece `PRINT`, avalia e emite `IMPR` | `p_stmt_print` emite `IMPR` |

---

## 5. Desafio 4.4 — Auditoria de código gerado por IA

Trecho auditado (fornecido no roteiro):
```python
def p_stmt_while(p):
    """stmt : WHILE '(' bool ')' stmt"""
    l1 = new_label()
    emit(f"L{l1}:")      # (A)
    emit(f"DSVF L{l2}")  # (B)
    emit(f"DSVS L{l1}")  # (C)
    emit(f"L{l2}:")      # (D)
```

### 5.1 Erros identificados
1. **Variável não definida:** `l2` é usada em (B) e (D), mas nunca criada com `new_label()`; o Python lançaria `UnboundLocalError`/`NameError`.
2. **Momento da redução e ordem de emissão:** no PLY, o corpo de `p_*` só roda quando a produção inteira é reduzida, isto é, depois que o `stmt` filho já foi reduzido. Assim, `L1:` e `DSVF L2` sairiam **depois** das instruções do corpo, quando deveriam sair antes. O corpo executaria sempre uma vez e o desvio de saída nunca evitaria o corpo.
3. **Condição nunca reavaliada:** como `L1:` seria emitido depois do código da condição, o `DSVS L1` voltaria para um ponto posterior ao teste; a condição não seria reavaliada, e o `DSVF` seguinte leria da pilha um valor que não é o resultado do teste.

### 5.2 Por que o código parece plausível
A sequência visual `(A) L1: → (B) DSVF L2 → corpo → (C) DSVS L1 → (D) L2:` reproduz o padrão de tradução de laço dos livros-texto. O que falta é a semântica *bottom-up* do LALR do PLY: uma ação não pode ficar "no meio" da produção, a menos que seja separada em não terminais auxiliares.

### 5.3 Versão correta
```python
WHILE_PENDING = []
LOOP_EXITS = []

def p_while_start(p):
    """while_start : """
    l1, l2 = new_label(), new_label()
    emit(f"L{l1}:")          # (A) rótulo de retorno — emitido ANTES do teste
    WHILE_PENDING.append((l1, l2))
    LOOP_EXITS.append(l2)    # permite que break encontre o rótulo de saída

def p_while_head(p):
    """while_head : WHILE '(' while_start bool ')'"""
    l1, l2 = WHILE_PENDING[-1]
    emit(f"DSVF L{l2}")      # (B) desvio condicional — emitido APÓS a condição e ANTES do corpo

def p_stmt_while(p):
    """stmt : while_head stmt"""
    l1, l2 = WHILE_PENDING.pop()
    LOOP_EXITS.pop()
    emit(f"DSVS L{l1}")      # (C) retorno ao início do laço
    emit(f"L{l2}:")           # (D) rótulo de saída
```

**Por que a decomposição em três regras funciona:**

A produção original `WHILE '(' bool ')' stmt` seria reduzida apenas **depois** que o `stmt` inteiro já foi traduzido. Ao decompor em `while_start` (vazio, antes do `bool`) e `while_head` (após o `bool`), o PLY executa cada ação no momento exato da sua redução no autômato LALR:

| Momento da redução | Regra | Instrução emitida |
|---|---|---|
| Antes de analisar a condição | `while_start :` | `L1:` |
| Após reduzir a condição (`bool`) | `while_head : WHILE '(' while_start bool ')'` | `DSVF L2` |
| Após reduzir o corpo (`stmt`) | `stmt : while_head stmt` | `DSVS L1` e `L2:` |

**Código MEPA gerado para `while.uc` (contador regressivo de 10 a 1):**
```
AMEM 4	; n address: 0
CRCT 10
ARMZ 0,0	; n
L1:              ← (A) while_start emite o rótulo de retorno
CRVL 0,0	; n
CRCT 0
CMMA             ← condição: n > 0
DSVF L2          ← (B) while_head emite o desvio condicional de saída
CRVL 0,0	; n
IMPR             ← corpo do laço
CRVL 0,0	; n
CRCT 1
SUBT
ARMZ 0,0	; n
DSVS L1          ← (C) retorno ao início
L2:              ← (D) rótulo de saída
```

Comprovação no MEPA: `while.uc` produz a saída `[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]`, confirmada na suíte de testes (Seção 3.1).

---

## 6. Divergências em relação ao compilador de referência

Para cada programa de teste, comparamos o código gerado pelo nosso compilador (pasta `mvpOutput/`) com o código esperado do compilador de referência Java (`uc-full`), desconsiderando comentários, a linha `AMEM 4 ; temp (ponteiro)` e a numeração absoluta dos rótulos (Seção 11.2 do roteiro).

Código gerado pelo nosso compilador para cada exemplo:

**`expr.uc`** — `int a; a = 1 + 2;`
```
AMEM 4	; a address: 0
CRCT 1
CRCT 2
SOMA
ARMZ 0,0	; a
```

**`decl.uc`** — `{ int a; float x; }`
```
AMEM 4	; a address: 0
AMEM 8	; x address: 4
```

**`precedencia.uc`** — `a = a + b * 3; a = (a + b) * 3;`
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

**`if.uc`** — `int a; if (a > 0) a = 1; else a = 2;`
```
AMEM 4	; a address: 0
CRVL 0,0	; a
CRCT 0
CMMA
DSVF L1
CRCT 1
ARMZ 0,0	; a
DSVS L2
L1:
CRCT 2
ARMZ 0,0	; a
L2:
```

**`while.uc`** — contador regressivo de 10 a 1
```
AMEM 4	; n address: 0
CRCT 10
ARMZ 0,0	; n
L1:
CRVL 0,0	; n
CRCT 0
CMMA
DSVF L2
CRVL 0,0	; n
IMPR
CRVL 0,0	; n
CRCT 1
SUBT
ARMZ 0,0	; n
DSVS L1
L2:
```

**`break.uc`** — `while (k <= 10)` com `if (k > 5) break`
```
AMEM 4	; k address: 0
CRCT 1
ARMZ 0,0	; k
L1:
CRVL 0,0	; k
CRCT 10
CMEG
DSVF L2
CRVL 0,0	; k
CRCT 5
CMMA
DSVF L3
DSVS L2	; break
L3:
CRVL 0,0	; k
IMPR
CRVL 0,0	; k
CRCT 1
SOMA
ARMZ 0,0	; k
DSVS L1
L2:
```

**`dowhile.uc`** — `do { print(x); x = x + 1; } while (x <= 5);`
```
AMEM 4	; x address: 0
CRCT 1
ARMZ 0,0	; x
L1:
CRVL 0,0	; x
IMPR
CRVL 0,0	; x
CRCT 1
SOMA
ARMZ 0,0	; x
CRVL 0,0	; x
CRCT 5
CMEG
DSVT L1
L2:
```

**`fib.uc`** — Fibonacci com `read(n)`, laço `while (i < n)`
```
AMEM 4	; n address: 0
AMEM 4	; a address: 4
AMEM 4	; b address: 8
AMEM 4	; t address: 12
AMEM 4	; i address: 16
LEIT
ARMZ 0,0	; n
CRCT 0
ARMZ 0,4	; a
CRCT 1
ARMZ 0,8	; b
CRCT 0
ARMZ 0,16	; i
L1:
CRVL 0,16	; i
CRVL 0,0	; n
CMME
DSVF L2
CRVL 0,4	; a
CRVL 0,8	; b
SOMA
ARMZ 0,12	; t
CRVL 0,8	; b
ARMZ 0,4	; a
CRVL 0,12	; t
ARMZ 0,8	; b
CRVL 0,16	; i
CRCT 1
SOMA
ARMZ 0,16	; i
DSVS L1
L2:
CRVL 0,0	; n
IMPR
CRVL 0,4	; a
IMPR
```

### Resumo das divergências

| Programa | Resultado | Divergências e explicação |
|---|---|---|
| `expr.uc` | ✅ Equivalente | Sem divergências estruturais. A referência emite `AMEM 4 ; temp` antes das instruções — ignorado conforme Seção 11.2. |
| `decl.uc` | ✅ Equivalente | Sem divergências. A referência também emite `AMEM 4` para `int` e `AMEM 8` para `float`, com `OFFSET` idêntico. |
| `precedencia.uc` | ✅ Equivalente | Sem divergências na ordem das instruções. Precedência da multiplicação (`MULT` antes de `SOMA`) e dos parênteses (`SOMA` antes de `MULT`) emitida corretamente. |
| `if.uc` | ✅ Equivalente | Estrutura `DSVF / corpo-then / DSVS / rótulo-else / corpo-else / rótulo-fim` idêntica à da referência. Numeração dos rótulos (`L1`, `L2`) pode variar — irrelevante para semântica. |
| `while.uc` | ✅ Equivalente | Estrutura `rótulo-inicio / condição / DSVF / corpo / DSVS-retorno / rótulo-fim` idêntica. A referência emite `AMEM 4 ; temp` — ignorado (Seção 11.2). |
| `break.uc` | ✅ Equivalente (com melhoria) | A referência valida o `break` mas **não emite** o `DSVS` de escape (Seção 10.2). Nosso compilador emite `DSVS L2 ; break`, completando corretamente o desvio para fora do laço. |
| `dowhile.uc` | ✅ Equivalente | Estrutura `rótulo-inicio / corpo / condição / DSVT-retorno` correta para o laço pós-testado. A referência não prevê `do-while` (Desafio 4.1); comparação feita com o padrão esperado da especificação. |
| `fib.uc` | ✅ Equivalente | `LEIT`/`IMPR`, `ARMZ`/`CRVL` e estrutura do laço `while` com cinco variáveis idênticos ao esperado. |

Pontos gerais:
1. **Numeração de rótulos:** varia com a sequência de reduções do autômato LALR; não altera a semântica dos desvios.
2. **Ponteiro temporário:** o gerador Java emite `AMEM 4 ; temp (ponteiro)`. Conforme a Seção 11.2, esse detalhe foi ignorado na comparação e não é emitido pelo nosso compilador.
3. **Melhoria no `break`:** a referência apenas valida a presença do `break` no laço, sem emitir o `DSVS` (Seção 10.2). O nosso emite o desvio para o rótulo de saída do laço mais interno.

---

## 7. Dificuldades encontradas e soluções

1. **Regra inicial no PLY — axioma incorreto:**  
   A regra auxiliar `empty` foi declarada antes de `p_program` e sem a diretiva `start = 'program'`. O PLY define o axioma como a primeira função `p_*` encontrada; como `empty` aparecia primeiro, qualquer programa não vazio gerava erro de sintaxe imediatamente. A saída original do erro não foi registrada, pois o problema foi identificado na fase inicial de desenvolvimento.  
   *Solução:* declarar `start = 'program'` na linha 114 do arquivo e mover `p_empty` para depois de todas as regras gramaticais (linha 367), garantindo que `program` seja reconhecido pelo PLY como símbolo inicial.

2. **Fim de linha no lexer — `lineno` nunca incrementado:**  
   O caractere `\n` estava incluído em `t_ignore = ' \t\n'`. Com isso, o lexer descartava silenciosamente as quebras de linha sem incrementar o contador de linhas, fazendo com que qualquer mensagem de erro (variável não declarada, token inesperado) sempre apontasse a **linha 1**, independente de onde o erro ocorria.  
   *Solução:* remover `\n` de `t_ignore` e adicionar a função:
   ```python
   def t_newline(t):
       r'\n+'
       t.lexer.lineno += len(t.value)
   ```
   Isso garante que `p.lineno(n)` retorna o número de linha correto nas ações semânticas (por exemplo, `f"linha {p.lineno(1)}: variavel nao declarada"`).

3. **Mnemônicos relacionais incorretos do MEPA:**  
   Em uma versão anterior do compilador, os operadores relacionais foram mapeados com mnemônicos errados. Os erros identificados foram:
   - `==` estava mapeado para `CMEG` (deveria ser `CMIG` — *compara igual*)
   - `<=` também usava `CMEG`, sobrescrevendo o mapeamento anterior
   - `<` usava `CMMEN` (mnemônico inexistente na MEPA 5.0; correto é `CMME`)
   - `>` usava `CMAI` (mnemônico inexistente; correto é `CMMA`)
   
   *Solução:* alinhar todos os mnemônicos com a especificação oficial da MEPA 5.0:

   | Operador | Mnemônico correto | Erro anterior |
   |---|---|---|
   | `==` | `CMIG` | `CMEG` |
   | `!=` | `CMDG` | — |
   | `<`  | `CMME` | `CMMEN` |
   | `<=` | `CMEG` | duplicado com `==` |
   | `>`  | `CMMA` | `CMAI` |
   | `>=` | `CMAG` | — |

4. **Conflito de escopo entre `t_DIVI` e comentários de bloco `/* */`:**  
   A regra `t_DIVI = r'/'` era aplicada antes da regra `t_COMMENT_BLOCK`. Como o PLY prioriza regras literais por comprimento, o `/` isolado era consumido antes de o lexer ter chance de reconhecer `/*`. Isso fazia comentários de bloco gerarem tokens `DIVI` espúrios.  
   *Solução:* implementar `t_COMMENT_BLOCK` como função (não como string), pois funções têm precedência sobre strings no PLY, resolvendo o conflito de forma limpa:
   ```python
   def t_COMMENT_BLOCK(t):
       r'/\*(.|\\n)*?\*/'
       t.lexer.lineno += t.value.count('\n')
   ```

---

## 8. Declaração de Uso de Inteligência Artificial

Em conformidade com as diretrizes da Seção 14 deste laboratório e a escala AIAS:

*Declaração individual:*  
**Fabrício Rickelmer Souza Duarte:** Confirmo que todas as ações e decisões relatadas foram rigorosamente compreendidas e implementadas, garantindo o domínio pleno sobre a tradução dirigida por sintaxe e a geração de código para a máquina de pilha MEPA.

**Esther de Faria** Declaro que contribui para a elaboração dos Passos 1 a 3 que utiliza da IA como auxiliar para compreender mais sobre o uso da biblioteca ply, o que me proporcionou um maior aprendizado a cerca do tema. 

**Luiza Alves de Oliveira Vieira** Também confirmo que trabalhei na implementação dos Passos 4 e 5 para implementar as regras auxiliares marcadores, assim como o meu colega Fabrício, ajudei-o no gerenciamento das pilhas de atributos herdados (`IF_PENDING`, `WHILE_PENDING`, `LOOP_EXITS`).

**Thamara Luiza Bicalho Oliveira Silva**: Declaro que atuei no nível 4 como Auditora, analisando criticamente o código que foi gerado pela IA, modificando os seus erros e aprendendo com eles, de maneira que o trabalho foi entregue com êxito.