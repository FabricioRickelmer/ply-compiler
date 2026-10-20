# Compilador µC com Tradução Dirigida por Sintaxe (PLY)

Laboratório 1 da disciplina **ECOI2219 — Compiladores** (UNIFEI - Campus Itabira).

Compilador para a linguagem $\mu\text{C}$ implementado em Python utilizando a biblioteca **PLY (Python Lex-Yacc)**, com geração de código voltada para a máquina de pilha **MEPA 5.0**.

---

## Estrutura do Projeto

Organizado conforme padrões de engenharia de software (`src/` layout):

```
ply-compiler/
├── .gitignore
├── README.md               # Instruções de compilação, execução e requisitos
├── mvpOutput/              # Saídas MEPA geradas automaticamente (uma por teste)
├── src/                    # Código-fonte do compilador
│   └── lab1_tds.py         # Compilador (Léxico, Sintático e Tradução Dirigida)
├── tests/                  # Bateria de testes
│   └── test_suite.py       # Script de automação de testes
├── mepa/                   # Interpretador da Máquina Virtual MEPA 5.0
│   └── mepa_pt.py
├── examples/               # Programas de teste na linguagem µC (.uc)
│   ├── expr.uc             # Expressões básicas
│   ├── decl.uc             # Declarações int (4B) e float (8B)
│   ├── precedencia.uc      # Verificação de precedência (+, -, *, /)
│   ├── if.uc               # Comando condicional if-else
│   ├── while.uc            # Laço while
│   ├── break.uc            # Comando break em laço
│   ├── dowhile.uc          # Desafio 4.1: comando pós-testado do-while
│   └── fib.uc              # Desafio 4.2: Fibonacci com read/print e blocos
└── docs/                   # Documentação e especificações
    ├── relato_lab1.md      # Relato técnico da equipe (decisões, evidências e AIAS)
    └── Trabalho PLY - Laboratório 1 - Módulo 4.pdf
```

---

## Como Executar

### 1. Requisitos
- Python 3.10 ou superior
- Biblioteca `ply`:
  ```bash
  pip install ply
  ```

### 2. Compilar um programa em µC
```bash
python src/lab1_tds.py examples/while.uc > mvpOutput/while.txt
```

### 3. Executar o código gerado na MEPA
```bash
python mepa/mepa_pt.py --progfile mvpOutput/while.txt --silent
```

### 4. Executar toda a bateria de testes automatizados
```bash
python tests/test_suite.py
```
