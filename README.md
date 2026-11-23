# Compilador µC com Tradução Dirigida por Sintaxe, Análise Semântica e Backpatching (PLY)

Laboratórios 1, 2 e 3 da disciplina **ECOI2219 — Compiladores** (UNIFEI - Campus Itabira).  
Compilador para a linguagem $\mu\text{C}$ implementado em Python utilizando a biblioteca **PLY (Python Lex-Yacc)**, com geração de código voltada para a máquina de pilha **MEPA 5.0**.

---

## Estrutura do Projeto

Organizado conforme padrões de engenharia de software (`src/` layout):

```
ply-compiler/
├── .gitignore
├── README.md                   # Instruções de compilação, execução e requisitos
├── src/                        # Código-fonte do compilador
│   ├── lab1_tds.py             # Laboratório 1: Tradução Dirigida por Sintaxe (TDS)
│   ├── lab2_semantica.py       # Laboratório 2: Análise Semântica e Síntese de Tipos
│   └── lab3_gerador.py         # Laboratório 3: Geração de Código (MVP) com Backpatching
├── tests/                      # Bateria de testes
│   ├── test_suite.py           # Testes do Laboratório 1
│   ├── test_errors.py          # Bateria de 7 erros semânticos/léxicos (Seção 6.1 do Lab 2)
│   ├── test_suite_lab2.py      # Bateria integrada de programas válidos e erros (Lab 2)
│   └── test_suite_lab3.py      # Bateria integrada com Fibonacci e desafios (Lab 3)
├── mepa/                       # Interpretador da Máquina Virtual MEPA 5.0
│   └── mepa_pt.py
├── tools/                      # Ferramentas auxiliares e compilador de referência Java
│   ├── uc-compilador.jar       # Compilador oficial da referência (UNIFEI)
│   └── RefCompiler.java        # CLI wrapper para testes comparativos com a referência
├── examples/                   # Exemplos válidos e bateria de erros (.uc)
│   ├── *.uc                    # 15 programas válidos (expr, decl, if, while, fib, charlit, etc.)
│   └── errors/                 # 7 casos de erro da bateria oficial do Lab 2
├── uc-full/examples/           # Espelho da estrutura oficial de exemplos
└── docs/                       # Documentação técnica
    ├── relato_lab1.md          # Relato técnico do Laboratório 1
    ├── relato_lab2.md          # Relato técnico do Laboratório 2
    ├── relato_lab3.md          # Relato técnico do Laboratório 3 (Backpatching)
    └── trabalho-ply-relato.md  # Relato técnico consolidado
```

---

## Como Executar

### 1. Requisitos
- Python 3.10 ou superior
- Java Runtime Environment (JRE) / JDK (para executar o compilador de referência)
- Biblioteca `ply`:
  ```bash
  pip install ply
  ```

### 2. Laboratório 3: Geração de Código com Backpatching (Recomendado)
Para compilar um programa utilizando o gerador de código com listas de pendências (*backpatching*):
```bash
python src/lab3_gerador.py examples/fib.uc
```

Para redirecionar as instruções MEPA geradas e executá-las diretamente no interpretador:
```bash
python src/lab3_gerador.py examples/fib.uc > output.mepa
python mepa/mepa_pt.py --progfile output.mepa --silent
```

### 3. Teste Integrador: Fibonacci com Entradas
Executar o programa Fibonacci fornecendo as entradas $1$, $10$ ou $20$:
```bash
echo 10 | python mepa/mepa_pt.py --progfile output.mepa --silent
# Saída esperada: 10 e 55
```

### 4. Execução da Suíte Completa de Testes do Laboratório 3
Valida automaticamente os 15 programas válidos na MEPA, o teste integrador de Fibonacci nas 3 entradas, os testes dos desafios do roteiro (5.2, 5.3 e blocos) e a bateria de erros:
```bash
python tests/test_suite_lab3.py
```

### 5. Execução dos Laboratórios Anteriores
- **Laboratório 1:** `python tests/test_suite.py`
- **Laboratório 2:** `python tests/test_suite_lab2.py`
- **Bateria de Erros:** `python tests/test_errors.py`

### 6. Comparação com o Compilador de Referência (Java)
Para testar qualquer arquivo `.uc` diretamente no compilador oficial de referência da UNIFEI:
```bash
java -cp "tools;tools/uc-compilador.jar" RefCompiler examples/fib.uc
```
O código MEPA gerado pela referência é gravado em `mvpOutput.txt`.
