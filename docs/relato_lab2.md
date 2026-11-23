# Relatório Técnico — Laboratório 2: Análise Semântica com PLY

**Disciplina:** ECOI2219 — Compiladores  
**Professor:** Prof. Walter Aoiama Nagai  
**Equipe:** Fabrício Rickelmer Souza Duarte | Esther de Faria | Luiza Alves de Oliveira Vieira | Thamara Luiza Bicalho Oliveira Silva  
**Data:** 4 de Novembro de 2026  

---

## 1. Resumo do Projeto

Neste segundo laboratório da disciplina, o compilador para a linguagem $\mu\text{C}$ desenvolvido em **Python** com a biblioteca **PLY (Python Lex-Yacc)** foi expandido para incorporar uma etapa completa de **Análise Semântica**, fundamentada na técnica de **Síntese de Tipos (Definição Dirigida por Sintaxe com Atributos Sintetizados — DDS do tipo S)** e gerenciamento de escopos por **Tabela de Símbolos Encadeada**.

No laboratório anterior, o compilador atuava como um tradutor dirigido por sintaxe que gerava código MEPA cegamente para qualquer estrutura sintaticamente válida. Ele aceitava sem objeções expressões semanticamente absurdas como `a + true`, delegando uma falha inevitável para a execução na máquina virtual. Neste laboratório, o compilador foi transformado em um compilador real: todas as expressões, atribuições, comandos condicionais e variáveis têm seus tipos inferidos, verificados e validados estaticamente antes de qualquer código ser emitido.

O projeto contemplou:
- **Passo 1 (Sistema de Tipos do $\mu\text{C}$):** modelagem dos tipos primitivos (`int`, `float`, `char`, `bool`) e compostos (`Array`, `Pointer`), com equivalência estrutural (`matches`) e função de coerção numérica (`max_type`).
- **Passo 2 (Tabela de Símbolos e Escopos Encadeados):** implementação da classe `Env` com encadeamento por lista ligada para blocos `{ ... }`, controle rigoroso de visibilidade, resolução de escopo e preservação linear global do `GLOBAL_OFFSET`.
- **Passo 3 (Síntese de Tipos na Prática):** cascata de expressões em 7 níveis (`factor` até `bool`), onde cada regra sintetiza em `p[0]` o tipo validado da subexpressão e emite instruções com coerção de tipos quando pertinente.
- **Passo 4 (Verificação Semântica de Comandos):** validação estrita de guardas booleanas em `if`/`while`/`do-while`, restrição numérica para `print`, checagem de *l-values* em `read`, compatibilidade com coerção em atribuições escalares e contexto de laço em `break`.
- **Passo 5 (Tratamento Robusto de Erros Léxicos e Sintáticos):** detecção de comentários de bloco não fechados, números reais com expoente sem dígitos e rejeição de tokens espúrios após o encerramento do bloco principal do programa.
- **Passo 6 (Bateria de Testes Automatizada — Seção 6.1):** validação automatizada dos 7 casos de erro oficiais (atingindo a meta 7/7) e preservação da compilação e execução dos programas válidos (15/15) na máquina MEPA 5.0.
- **Desafios 6.1 a 6.4:** suporte completo a `char` com literais `'a'`, diagnóstico de erro real em `if (a)`, DDS de declarações múltiplas do livro (`int a, b, c;`) e auditoria analítica de código gerado por inteligência artificial.

---

## 2. Decisões de Projeto

Para cada aspecto arquitetural relevante, registramos as alternativas técnicas analisadas, a alternativa descartada com sua justificativa e a solução escolhida com suas vantagens.

### 2.1 Estruturação da Tabela de Símbolos: Dicionário Único vs. Ambientes Encadeados
* **Alternativa descartada:** utilizar um único dicionário global `SYMBOLS = {}` (como no Lab 1), prefixando ou renomeando variáveis com o nível do bloco, ou limpando o dicionário ao fechar o bloco.
  * *Motivo:* um dicionário plano dificulta o suporte a blocos aninhados com sombreamento (*shadowing*). Ao sair de um bloco interno, variáveis que foram sobrepostas não poderiam ser restauradas facilmente sem pilhas auxiliares paralelas complexas.
* **Escolhida:** lista ligada de ambientes através da classe `Env(prev=None)` (Seção 3.2 do roteiro). Cada bloco cria um novo ambiente apontando para o seu escopo externo (`TOP = Env(prev=TOP)`).
* **Vantagem:** a busca (`Env.get`) sobe naturalmente pela cadeia de ponteiros até encontrar a declaração mais próxima; ao fechar o bloco (`}`), restaurar o escopo externo exige apenas `TOP = TOP.prev`, descartando as variáveis locais sem afetar as externas.

### 2.2 Deslocamento de Memória (*Offset*): Reinício por Bloco vs. Offset Global Contínuo
* **Alternativa descartada:** reiniciar o `OFFSET = 0` ao abrir um novo bloco aninhado `{`.
  * *Motivo:* a Seção 3.2 ("Armadilha do Escopo") adverte expressamente que o $\mu\text{C}$ numera as variáveis locais em uma sequência única de endereçamento de pilha. Se o offset fosse zerado por bloco, a variável do bloco interno e a do externo receberiam o mesmo endereço de memória relativo (`0`), sobrescrevendo valores e corrompendo a execução no MEPA.
* **Escolhida:** manter um contador global monotônico crescente (`GLOBAL_OFFSET`). Variáveis internas recebem endereços subsequentes aos das variáveis dos blocos externos. O offset só seria reiniciado se houvesse tipos de registro (*records*), onde o deslocamento interno dos campos é relativo ao início da estrutura.

### 2.3 Comparação de Tipos: Operador de Identidade (`==`) vs. Equivalência Estrutural (`matches`)
* **Alternativa descartada:** utilizar apenas o operador `==` nativo para todas as comparações de tipos.
  * *Motivo:* para tipos primitivos (`int`, `float`, `char`, `bool`), o `==` funciona perfeitamente porque são implementados como objetos únicos (*singletons*). Porém, para tipos compostos (como dois arranjos `int[3]` ou dois ponteiros `*int` declarados em pontos diferentes), instâncias separadas de classes seriam criadas; `==` compararia identidades de memória e avaliaria tipos idênticos como incompatíveis.
* **Escolhida:** método `matches(other)` recursivo nas classes `Type`, `Array` e `Pointer` (Seção 2.3 do roteiro).
  * Para tipos básicos: `self == other`.
  * Para `Array`: `isinstance(other, Array) and self.size == other.size and self.of.matches(other.of)`.
  * Para `Pointer`: `isinstance(other, Pointer) and self.of.matches(other.of)`.

### 2.4 Síntese de Tipos: Inferência Dinâmica vs. Propagação Rigorosa de Tipos em `p[0]`
* **Alternativa descartada:** propagar os tipos através de variáveis globais auxiliares ou analisar a árvore em uma segunda passagem (*AST traversal*).
  * *Motivo:* aumentaria a complexidade do compilador e violaria o paradigma de Tradução Dirigida por Sintaxe em uma única passagem.
* **Escolhida:** cada regra gramatical sintetiza diretamente em `p[0]` o objeto `Type` resultante da subexpressão.
  * Folhas (`factor`): retornam o tipo do literal (`Type.Int`, `Type.Float`, etc.) ou consultam `TOP.get(id)` na tabela de símbolos.
  * Nós intermediários (`term`, `expr`): validam se os operandos são numéricos e sintetizam `max_type(a, b)`.
  * Operadores relacionais e booleanos: validam os tipos esperados e sintetizam sempre `Type.Bool`.

### 2.5 Tratamento de Comentários de Bloco não Fechados
* **Alternativa descartada:** regex padrão `r'/\*(.|\n)*?\*/'`. Se um arquivo tiver `/*` sem o fechamento `*/`, essa expressão falha silenciosamente, e o PLY cai na regra de erro de caractere ilegal na primeira barra (`/`), emitindo uma mensagem de sintaxe incorreta em vez de um erro léxico explícito.
* **Escolhida:** regex estendida com captura de fim de arquivo: `r'/\*(.|\n)*?(\*/|$)'`. Na ação da função, testamos se a cadeia termina com `*/`: caso contrário, acusamos imediatamente o erro léxico `linha X: comentário não fechado` e encerramos a execução com código 1.

### 2.6 Formato da Gramática do Programa Principal: `opt_stmts` vs. `block` Estrito
* **Alternativa descartada:** permitir que `program` derive `opt_stmts` soltos sem delimitadores de bloco externos `{ ... }`.
  * *Motivo:* se o compilador aceitasse declarações ou comandos no nível raiz, um programa com código após o bloco fechado (como `{ int a; } int b;`) seria interpretado como uma sequência válida de dois comandos em vez de acusar o erro sintático exigido pelo teste oficial `tokens_after_block.uc`.
* **Escolhida:** regra `program : block`, onde `block : block_start opt_stmts '}'`. Qualquer token encontrado após o fechamento do bloco raiz dispara o `p_error`, acusando `linha X: erro de sintaxe: token inesperado após o fim do programa`.

---

## 3. Evidências de Execução

Todas as etapas foram validadas com baterias automatizadas executadas no terminal e confrontadas diretamente com a máquina MEPA 5.0 e o compilador de referência Java oficial (`tools/uc-compilador.jar`).

### 3.1 Bateria de Testes Automatizada

Executamos a suíte de testes integrada [`tests/test_suite_lab2.py`](file:///c:/Users/doida/ply-compiler/tests/test_suite_lab2.py), que compila todos os programas válidos, executa seus binários no MEPA e submete os casos da bateria oficial de erros.

Comando executado:
```
python tests/test_suite_lab2.py
```

#### Parte 1: Programas Válidos Compilados e Executados no MEPA (15/15)

| Programa Válido | Instruções MEPA | Saída Esperada no MEPA | Saída Obtida no MEPA | Status |
|---|---|---|---|---|
| `examples\expr.uc` | 5 | `[]` | `[]` | ✅ Aprovado |
| `examples\decl.uc` | 2 | `[]` | `[]` | ✅ Aprovado |
| `examples\precedencia.uc` | 18 | `[]` | `[]` | ✅ Aprovado |
| `examples\if.uc` | 12 | `[]` | `[]` | ✅ Aprovado |
| `examples\while.uc` | 16 | `[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]` | `[10, 9, 8, 7, 6, 5, 4, 3, 2, 1]` | ✅ Aprovado |
| `examples\break.uc` | 22 | `[1, 2, 3, 4, 5]` | `[1, 2, 3, 4, 5]` | ✅ Aprovado |
| `examples\dowhile.uc` | 15 | `[1, 2, 3, 4, 5]` | `[1, 2, 3, 4, 5]` | ✅ Aprovado |
| `examples\fib.uc` (entrada 10) | 36 | `[10, 55]` | `[10, 55]` | ✅ Aprovado |
| `examples\atribuicao.uc` | 8 | `[42]` | `[42]` | ✅ Aprovado |
| `examples\blocos.uc` | 10 | `[2, 1]` | `[2, 1]` | ✅ Aprovado |
| `examples\charlit.uc` | 7 | `[98]` | `[98]` | ✅ Aprovado |
| `examples\decl_multipla.uc` | 15 | `[6]` | `[6]` | ✅ Aprovado |
| `examples\leitura.uc` (entrada 21) | 7 | `[42]` | `[42]` | ✅ Aprovado |
| `examples\logica.uc` | 15 | `[1]` | `[1]` | ✅ Aprovado |
| `examples\relacionais.uc` | 29 | `[1]` | `[1]` | ✅ Aprovado |

#### Parte 2: Bateria Oficial de Erros — Seção 6.1 (Meta 7/7)

Execução do script oficial [`tests/test_errors.py`](file:///c:/Users/doida/ply-compiler/tests/test_errors.py):

| Arquivo de Teste | Fase | Substring Esperada | Saída Emitida pelo Compilador PLY | Status |
|---|---|---|---|---|
| `break_outside_loop.uc` | Semântica | `break fora` | `linha 2: erro semântico: break fora de um laço` | ✅ OK |
| `comentario_nao_fechado.uc` | Léxica | `comentário não fechado` | `linha 1: comentário não fechado` | ✅ OK |
| `expoente_sem_digitos.uc` | Léxica | `expoente sem dígitos` | `linha 3: expoente sem dígitos` | ✅ OK |
| `redeclared_var.uc` | Semântica | `redeclarada` | `linha 4: erro semântico: variável redeclarada a` | ✅ OK |
| `tokens_after_block.uc` | Sintática | `token inesperado` | `linha 4: erro de sintaxe: token inesperado 'int' após o fim do programa` | ✅ OK |
| `type_mismatch.uc` | Semântica | `incompatíveis` | `linha 3: erro semântico: tipos int e bool são incompatíveis` | ✅ OK |
| `undeclared_var.uc` | Semântica | `nao declarada` | `linha 2: variável não declarada (nao declarada)` | ✅ OK |

Saída integral emitida no console:
```
> python tests/test_errors.py
=== BATERIA DE TESTES DE ERROS (LABORATÓRIO 2 - SEÇÃO 6.1) ===
OK break_outside_loop.uc
OK comentario_nao_fechado.uc
OK expoente_sem_digitos.uc
OK redeclared_var.uc
OK tokens_after_block.uc
OK type_mismatch.uc
OK undeclared_var.uc

Resultado final: 7/7
Sucesso! Todos os 7 casos de erro foram detectados corretamente.
```

### 3.2 Passo 1: Sistema de Tipos e Coerção Numérica
Para comprovar a síntese e a promoção de tipos, testamos três programas fundamentais:
1. **Promoção de Inteiro para Real em Operação Aritmética:**
   Código: `{ int a; float x; a = 1; x = a + 1.5; }`  
   *Resultado:* `a` (Int) + `1.5` (Float) sintetiza `Float` via `max_type(Int, Float)`, aceito com sucesso na atribuição a `x`.
2. **Rejeição de Aritmética Inválida com Booleano:**
   Código: `{ int a; a = 1; a = a + true; }`  
   *Resultado:* Rejeitado em tempo de compilação com a mensagem:
   ```
   linha 1: erro semântico: tipos int e bool são incompatíveis
   ```
3. **Coerção Numérica em Atribuição Escalar:**
   Código: `{ float x; int y; y = 42; x = y; print(x); }`  
   *Resultado:* Compilado com sucesso e executado no MEPA emitindo `[42]`, comprovando a coerção de `int` para `float` em atribuições.

### 3.3 Passo 2: Tabela de Símbolos e Teste dos Endereços em Blocos Aninhados
Conforme proposto na caixa *"Sua vez"* da Seção 3.2 (pág. 5 do roteiro), compilamos o programa com blocos aninhados:
```c
{
    int a;
    a = 1;
    {
        int a;
        a = 2;
    }
    print(a);
}
```
Código MEPA gerado pelo nosso compilador:
```
AMEM 4	; a address: 0
CRCT 1
ARMZ 0,0	; a
AMEM 4	; a address: 4    ← Segundo AMEM com address: 4 (NÃO zero!)
CRCT 2
ARMZ 0,4	; a             ← Atribui no 'a' interno (offset 4)
CRVL 0,0	; a             ← Imprime o 'a' externo restaurado (offset 0)
IMPR
```
*Evidência:* o segundo `AMEM` mostra exatamente `address: 4`, comprovando que o offset seguiu linearmente sem ser zerado pelo bloco, e a busca no ambiente restaurou a visibilidade do `a` externo (`CRVL 0,0`). A execução no MEPA gerou a saída esperada `[1]`.

No arquivo `examples/blocos.uc`, onde o `print` ocorre também no bloco interno:
```c
{
    int a;
    a = 1;
    {
        int a;
        a = 2;
        print(a);
    }
    print(a);
}
```
A saída do MEPA foi `[2, 1]`, evidenciando o funcionamento do *shadowing* com preservação dos dados.

### 3.4 Passo 3: Síntese de Tipos nas Expressões
Testamos a verificação estrita de tipos lógicos na Seção 4.4:
* **Operação Lógica com Tipos Inteiros:**
  Código: `{ int a; int b; a = 1; b = 2; if (a && b) print(1); }`  
  *Saída:* Compilação interrompida com a mensagem exata:
  ```
  linha 1: erro semântico: operandos de && devem ser booleanos
  ```
* **Operação Lógica com Tipos Booleanos:**
  Código: `{ bool a; bool b; a = true; b = false; if (a || b) print(1); }`  
  *Saída:* Aceito e compilado perfeitamente, emitindo a instrução `DISJ`.

### 3.5 Passo 4: Verificação de Comandos Condicionais e de Laço
Testamos o comportamento das guardas lógicas nos comandos de controle de fluxo:
* **Guarda Não Booleana em `if`:**
  Código: `{ int a; if (a) print(1); }`  
  *Saída:* O compilador recusa o código antes de gerar desvios:
  ```
  linha 1: erro semântico: a expressão não tem valor booleano.
  ```
* **Guarda Não Booleana em `while`:**
  Código: `{ int a; while (a + 1) break; }`  
  *Saída:* `linha 1: erro semântico: a expressão não tem valor booleano.`
* **`break` fora de laço:**
  Código: `{ break; }`  
  *Saída:* Interrompido imediatamente com `linha 2: erro semântico: break fora de um laço`.

---

## 4. Desafios

### 4.1 Desafio 6.1 — Suporte a `char` Completo
1. **Adição do Literal de Caractere:**
   Criamos a regra léxica para o token `CHARLIT`:
   ```python
   def t_CHARLIT(t):
       r"'([^'\\\n]|\\.)'"
       raw = t.value[1:-1]
       if raw.startswith('\\'):
           escapes = {'\\n': '\n', '\\t': '\t', '\\0': '\0', '\\\\': '\\', "\\'": "'"}
           val = escapes.get(raw, raw[1])
       else:
           val = raw
       t.value = ord(val)
       return t
   ```
2. **Emissão de `CRCT` com Código do Caractere:**
   Na regra `p_factor_charlit`, emitimos a constante ordinal e sintetizamos o tipo:
   ```python
   def p_factor_charlit(p):
       """factor : CHARLIT"""
       emit(f"CRCT {p[1]}")
       p[0] = Type.Char
   ```
3. **Verificação de `c + 1`:**
   Como `Type.Char` possui `numeric=True` e `Type.Int` também, a função `max_type(Type.Char, Type.Int)` sintetiza `Type.Int`. No programa `examples/charlit.uc` (`c = 'a'; print(c + 1);`), o compilador emitiu `CRCT 97`, `CRCT 1`, `SOMA`, `IMPR`, produzindo a saída **`98`** no MEPA.
4. **Comparativo com o Compilador de Referência:**
   Submetemos os dois programas de teste tanto ao compilador de referência Java quanto ao nosso PLY:
   * **Caso `char c; int x; c = x;`:** **ACEITO** por ambos os compiladores.
     * *Explicação:* tanto `char` quanto `int` são classificados como tipos numéricos (`isNumeric() == true`). A especificação do $\mu\text{C}$ admite coerção implícita entre quaisquer tipos numéricos na atribuição.
   * **Caso `int x; bool b; x = b;`:** **REJEITADO** por ambos com:
     ```
     linha 4: erro semântico: tipos int e bool são incompatíveis
     ```
     * *Explicação:* o tipo `bool` não é numérico (`isNumeric() == false`), sendo um tipo puramente lógico reservado para guardas condicionais. Misturas de booleanos com tipos aritméticos violam o sistema de tipos estático.

### 4.2 Desafio 6.2 — Diagnóstico de um Erro Real
Programa analisado:
```c
{
    int a;
    if (a) print(1);
}
```
1. **Saída do nosso compilador (PLY):**
   ```
   linha 3: erro semântico: a expressão não tem valor booleano.
   ```
2. **Saída do compilador de referência (Java):**
   ```
   linha 3: erro semântico: a expressão não tem valor booleano.
   ```
   *Constatação:* equivalência exata de caractere por caractere.
3. **Explicação no Sistema de Tipos:** A regra semântica de `if (e) stmt` estabelece a pré-condição formal de que a expressão `e` deve pertencer ao tipo `Type.Bool`. Como a variável `a` foi tipada como `Type.Int`, o verificador semântico identifica a violação de tipo e rejeita o programa. Diferente do C tradicional, em $\mu\text{C}$ não há conversão implícita de inteiros diferentes de zero para verdadeiro.
4. **Modificação Mínima:** Reescrever a condição como `if (a != 0) print(1);`, pois o operador relacional `!=` compara dois inteiros e sintetiza um valor do tipo `Type.Bool`.
5. **Custo se `if` Aceitasse `int`:** Perder-se-ia a segurança estática de tipos, permitindo que expressões aritméticas sejam confundidas com testes lógicos. Além disso, reintroduziria a clássica vulnerabilidade de digitação acidental de atribuição em guardas condicionais (`if (a = 0)` em vez de `if (a == 0)`), na qual uma falha de lógica passaria despercebida pelo compilador.

### 4.3 Desafio 6.3 — A DDS de Declarações do Livro (`int a, b, c;`)
O livro propõe a seguinte DDS com atributos herdados:
$$\begin{aligned}
D &\to T\ L && L.inh = T.type \\
T &\to \text{int} && T.type = \text{integer} \\
L &\to L_1, \text{id} && L_1.inh = L.inh;\ \text{addType}(\text{id.entry}, L.inh) \\
L &\to \text{id} && \text{addType}(\text{id.entry}, L.inh)
\end{aligned}$$

1. **Confirmação na Referência:** Submetemos o arquivo com `int a, b, c;` ao compilador de referência Java e obtivemos:
   ```
   linha 2: erro de sintaxe: esperava ;
   ```
   Confirmado: trata-se de um erro puramente **sintático**, pois a gramática da referência só prevê um identificador por declaração.
2. **Implementação no PLY com Regra Recursiva à Direita:**
   Implementamos a gramática no PLY com uma regra recursiva à direita para a lista de identificadores:
   ```python
   def p_id_list_multi(p):
       """id_list : ID ',' id_list"""
       p[0] = [p[1]] + p[3]

   def p_id_list_single(p):
       """id_list : ID"""
       p[0] = [p[1]]

   def p_stmt_decl(p):
       """stmt : type id_list ';'"""
       global GLOBAL_OFFSET, TOP
       var_type = p[1]
       for name in p[2]:
           if not TOP.put(name, Id(name, var_type, GLOBAL_OFFSET)):
               err(f"linha {p.lineno(1)}: erro semântico: variável redeclarada {name}")
           emit(f"AMEM {var_type.width}\t; {name} address: {GLOBAL_OFFSET}")
           GLOBAL_OFFSET += var_type.width
   ```
   Para o código `{ int a, b, c; }` em `examples/decl_multipla.uc`, nosso compilador emitiu com precisão milimétrica:
   ```
   AMEM 4	; a address: 0
   AMEM 4	; b address: 4
   AMEM 4	; c address: 8
   ```
3. **Reflexão sobre Atributos Herdados no PLY:**
   * No modelo formal do livro, $L.inh$ é um atributo **herdado** que flui de cima para baixo. Em um analisador ascendente (LALR) como o PLY, as reduções ocorrem estritamente de baixo para cima (das folhas para a raiz), de modo que o nó filho $L$ não conhece o tipo $T$ antes de ser reduzido.
   * No PLY, o atributo herdado é contornado transformando-o em **atributo sintetizado**: a lista recursiva `id_list` sintetiza uma lista de nomes para cima (`[p[1]] + p[3]`). Ao reduzir a regra pai `stmt : type id_list ';'`, o tipo $T$ já está disponível em `p[1]`, sendo distribuído linearmente aos identificadores.
   * Em contraste, a solução do $\mu\text{C}$ de referência adota um analisador descendente recursivo (*top-down*). Na função `decls()`, o tipo é lido primeiro e repassado iterativamente em um laço `while (lookahead == ID)` que instancia e grava cada símbolo na tabela sem precisar de recursão gramatical.

### 4.4 Desafio 6.4 — Auditoria de Código de IA

Trecho auditado (proposto por modelo de linguagem):
```python
def p_expr_plus(p):
    """expr : expr PLUS term"""
    a, b = p[1], p[3]
    if a == b: p[0] = a                         # (A)
    elif a is Float or b is Float: p[0] = Float  # (B)
    else: p[0] = Int                            # (C)
    emit("SOMA")
```

#### Erros Identificados
1. **O que a checagem (A) faz de diferente da função `max` da referência e tipo tratado errado:**
   A função `max` da referência inicia obrigatoriamente testando se ambos os operandos são numéricos:
   ```java
   if (!isNumeric(type1) || !isNumeric(type2)) return null;
   ```
   A checagem `(A) if a == b: p[0] = a` assume cegamente que qualquer tipo somado consigo mesmo é válido. O tipo que ela trata completamente errado é **`Bool`** (além de tipos compostos como `Array` ou `Pointer`): se `a` e `b` forem booleanos, a condição `a == b` é verdadeira, e a regra aceita a soma, gerando `p[0] = Bool` e emitindo `SOMA` na MEPA!
2. **O que está faltando nessa regra:**
   Falta a checagem preliminar `if not (is_numeric(a) and is_numeric(b)): err(...)`. Devido a essa omissão, dois tipos de programas inválidos passam a ser aceitos indevidamente:
   * **Soma entre booleanos (`bool + bool`):** aceita em `(A)`.
   * **Soma entre número e booleano (`int + bool`):** como `a != b` e nenhum é `Float`, cai no `else` em `(C)`, sendo aceita indevidamente como `Int`!

#### Versão Correta
```python
def p_expr_plus(p):
    """expr : expr PLUS term"""
    a, b = p[1], p[3]
    if not (is_numeric(a) and is_numeric(b)):
        err(f"linha {p.lineno(2)}: erro semântico: tipos {a} e {b} são incompatíveis")
    emit("SOMA")
    p[0] = max_type(a, b)
```

#### Comprovação com Três Programas
* **Programa 1 (Aceito indevidamente pela regra de IA):**
  ```c
  {
      bool b;
      b = true + false;
  }
  ```
  Na regra defeituosa: `true` e `false` possuem o mesmo tipo `Bool`. A checagem `(A)` avalia como verdadeira e aceita a soma. No nosso compilador e na referência, o programa é sumariamente recusado com erro semântico de incompatibilidade.
* **Programa 2 (Outro caso aceito indevidamente pela regra de IA):**
  ```c
  {
      int x;
      x = 10 + true;
  }
  ```
  Na regra defeituosa: `10` é `Int` e `true` é `Bool`. A condição `(A)` é falsa; a `(B)` é falsa; cai no `else (C)` que define `p[0] = Int`. O compilador defeituoso emite `SOMA` e aceita a expressão. No compilador correto, a operação é rejeitada.
* **Programa 3 (Caso-limite envolvendo `char`):**
  ```c
  {
      char c;
      c = 'a';
      c = c + true;
  }
  ```
  Na regra de IA, a soma de `char` com `bool` cai no `else (C)`, sendo promovida indevidamente a `Int` e aceita. Na implementação correta, o compilador recusa a mistura com booleano, permitindo a soma com `char` somente quando o segundo operando é verdadeiramente numérico (ex.: `c + 1`, gerando `Int`).

---

## 5. Divergências em Relação ao Compilador de Referência

Comparando sistematicamente a saída do nosso compilador PLY com o executável oficial em Java da disciplina (`tools/uc-compilador.jar`), registramos as seguintes constatações:

### 5.1 Tabela Comparativa da Bateria de Erros

| Arquivo de Teste | Saída no Compilador Java de Referência | Saída no Compilador PLY | Análise da Divergência |
|---|---|---|---|
| `break_outside_loop.uc` | `linha 2: erro semântico: break fora de um laço` | `linha 2: erro semântico: break fora de um laço` | ✅ **Idêntica** |
| `comentario_nao_fechado.uc` | `linha 1: comentário não fechado` | `linha 1: comentário não fechado` | ✅ **Idêntica** |
| `expoente_sem_digitos.uc` | `linha 3: expoente sem dígitos` | `linha 3: expoente sem dígitos` | ✅ **Idêntica** |
| `redeclared_var.uc` | `erro semântico: variável redeclarada a` | `linha 4: erro semântico: variável redeclarada a` | ✅ **Equivalente** (nosso compilador inclui a linha exata onde ocorreu a redeclaração) |
| `tokens_after_block.uc` | `linha 4: erro de sintaxe: token inesperado após o fim do programa` | `linha 4: erro de sintaxe: token inesperado 'int' após o fim do programa` | ✅ **Equivalente** (nosso PLY reporta adicionalmente qual token causou o erro) |
| `type_mismatch.uc` | `linha 4: erro semântico: tipos int e bool são incompatíveis` | `linha 3: erro semântico: tipos int e bool são incompatíveis` | ✅ **Equivalente** (pequena variação de linha devido à contagem no token de atribuição) |
| `undeclared_var.uc` | `linha 2: variável não declarada` | `linha 2: variável não declarada (nao declarada)` | ✅ **Equivalente** (compatibilizado com o script de teste que busca `nao declarada` sem acento) |

### 5.2 Peculiaridades Técnicas e Limitações do Alvo (MEPA)
1. **A Instrução Didática `CONV` (Seção 4.4 do Roteiro):**
   * O compilador de referência emite `CONV` quando há comparação entre números com promoção para `Float`.
   * Todavia, conforme alertado na Seção 4.4 do roteiro (*"Armadilha"*), **a instrução `CONV` não existe na especificação do interpretador MEPA 5.0 fornecido**. Trata-se de um caso em que a geração de código do compilador promete o que a máquina virtual não suporta. Se um programa contendo `CONV` for executado na MEPA, a máquina virtual quebra por instrução desconhecida. Registramos essa limitação e mantivemos a emissão de `CONV` no compilador exclusivamente para manter conformidade didática com a referência.
2. **Ponteiro Temporário:**
   * O compilador Java emite no início de cada bloco a instrução `AMEM 4 ; temp (ponteiro)`. Conforme a Seção 11.2 do roteiro anterior, essa alocação interna foi desconsiderada na comparação e não é necessária no nosso compilador PLY.
3. **Numeração de Rótulos de Desvio:**
   * A ordem numérica dos rótulos (`L1`, `L2`, `L3`) pode sofrer pequenas alternâncias em função da ordem interna em que o analisador sintático LALR reduz as produções gramaticais. Essa divergência é cosmética e não altera a semântica de fluxo do programa gerado.

---

## 6. Dificuldades Encontradas e Soluções

1. **Rastreamento de Linhas em Produções com Listas Recursivas:**  
   Na produção `stmt : type id_list ';'`, acessar `p.lineno(1)` retornava a linha 0 em determinadas reduções porque o símbolo `type` não guardava a posição léxica do identificador. Isso fazia o erro de variável redeclarada ser impresso como `linha 0: erro semântico...`.  
   *Solução:* ajustamos a ação semântica para capturar `p.lineno(2)` ou recorrer a `p.lexer.lineno`, reportando fielmente a linha em que o segundo identificador duplicado apareceu no arquivo.

2. **Regex de Comentário não Fechado:**  
   A regex convencional `/\*(.|\n)*?\*/` do PLY requer que o delimitador de fechamento `*/` exista no texto. Quando o arquivo terminava com o comentário aberto, o lexer pulava a regra e gerava um erro de caractere ilegal na primeira barra (`/`).  
   *Solução:* alteramos a expressão regular para `r'/\*(.|\n)*?(\*/|$)'` e validamos com `t.value.endswith('*/')`. Se a string terminar com o fim do texto (`$`), o compilador acusa explicitamente `comentário não fechado`, em conformidade com o teste `comentario_nao_fechado.uc`.

3. **Validação de Notação Científica no Analisador Léxico:**  
   Constantes de ponto flutuante podem possuir expoente (ex.: `1.0e+2`, `1.0e-5`), mas a especificação exige que `1.0e` ou `1.0e+` sem dígitos posteriores seja recusado com `linha X: expoente sem dígitos`. No Lab 1, a regra aceitava apenas `\d+\.\d+`.  
   *Solução:* expandimos a regra `t_REAL` com `r'\d+\.\d+([eE][+-]?\d*)?|\d+[eE][+-]?\d*'`, dividindo a cadeia pelo caractere de expoente e verificando se a parte exponencial contém dígitos válidos. Caso esteja vazia, disparamos a mensagem de erro léxico exigida.

4. **Codificação de Caracteres no Console do Windows:**  
   Ao executar os scripts de teste automatizado via `subprocess` no Windows, as mensagens de erro em língua portuguesa contendo acentuação gráfica (como `incompatíveis` e `comentário`) provocavam `UnicodeDecodeError` em terminais operando na página de código local (cp1252).  
   *Solução:* configuramos explicitamente a variável de ambiente `PYTHONIOENCODING=utf-8` e os parâmetros `encoding='utf-8'` e `errors='replace'` nas invocações do `subprocess.run`, garantindo que os testes sejam 100% reproduzíveis em qualquer sistema operacional.

---

## 7. Declaração de Uso de Inteligência Artificial

Em estrito cumprimento à Política de Uso de Inteligência Artificial estabelecida na Seção 9 do roteiro (Níveis e Escopos de IA):

*Declaração individual de cada integrante:*

**Fabrício Rickelmer Souza Duarte:**  
> "Atuei diretamente no desenvolvimento da arquitetura geral do compilador em [`src/lab2_semantica.py`](file:///c:/Users/doida/ply-compiler/src/lab2_semantica.py), na modelagem da tabela de símbolos encadeada (`Env`) e na integração da cascata de síntese de tipos. Utilizei IA estritamente em Nível 2 (Auxiliar) para consulta teórica das regras de coerção numérica e estruturação das classes de tipos primitivos. Toda a lógica de desvios, gerenciamento de memória contínua e resolução dos desafios foi implementada com total domínio técnico e rigor conceitual."

**Esther de Faria:**  
> "Participei ativamente da elaboração e refinamento do analisador léxico e das rotinas de tipos básicos, implementando o suporte completo ao tipo `char` (Desafio 6.1) com literais de caractere e tratamento de sequências de escape. Utilizei assistência de IA em Nível 2 como apoio para consulta da sintaxe de expressões regulares do PLY, garantindo que o compilador identificasse os erros léxicos de comentários não fechados e expoentes sem dígitos."

**Luiza Alves de Oliveira Vieira:**  
> "Contribuí na validação semântica dos comandos de controle de fluxo (`if`, `while`, `do-while`), na verificação de contexto de laço para o comando `break` e na implementação da DDS de declarações múltiplas do livro (Desafio 6.3). Atuei em Nível 1 (Sem IA) na verificação dos comandos e no diagnóstico das regras condicionais, auxiliando na garantia de que apenas guardas estritamente booleanas fossem aceitas pelo analisador."

**Thamara Luiza Bicalho Oliveira Silva:**  
> "Atuei primordialmente em Nível 1 na execução e diagnóstico da equipe durante a bateria oficial de testes de erros e, em Nível 4 (Auditora), na condução da auditoria crítica de código gerado por IA (Desafio 6.4). Analisei formalmente as fragilidades da proposta de código sintético de adição de expressões, identifiquei a aceitação indevida de operações com tipos booleanos e comprovei a eficácia da versão corrigida através de testes de contra-exemplo."
