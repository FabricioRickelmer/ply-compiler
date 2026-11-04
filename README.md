# Compilador µC com Tradução Dirigida por Sintaxe e Análise Semântica (PLY)

Laboratórios 1 e 2 da disciplina **ECOI2219 — Compiladores** (UNIFEI - Campus Itabira).  
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
│   └── lab2_semantica.py       # Laboratório 2: Análise Semântica e Síntese de Tipos
├── tests/                      # Bateria de testes
│   ├── test_suite.py           # Testes do Laboratório 1
│   ├── test_errors.py          # Bateria de 7 erros semânticos/léxicos (Seção 6.1 do Lab 2)
│   └── test_suite_lab2.py      # Bateria integrada de programas válidos e erros (Lab 2)
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
    ├── relato_lab2.md          # Relato técnico do Laboratório 2 (Seção 8.1)
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

### 2. Laboratório 2: Análise Semântica e Compilação
Para compilar um programa com análise semântica e verificação estática de tipos:
```bash
python src/lab2_semantica.py examples/fib.uc
```

Para redirecionar as instruções MEPA geradas e executá-las:
```bash
python src/lab2_semantica.py examples/fib.uc > output.mepa
python mepa/mepa_pt.py --progfile output.mepa --silent
```

### 3. Execução da Bateria de Erros (Laboratório 2 - Seção 6.1)
Executa a verificação dos 7 programas que devem ser rejeitados pelo compilador (meta 7/7):
```bash
python tests/test_errors.py
```

### 4. Execução da Bateria Integrada Completa
Valida tanto os 15 programas válidos com execução na MEPA quanto os 7 casos de erro:
```bash
python tests/test_suite_lab2.py
```

### 5. Comparação com o Compilador de Referência (Java)
Para testar qualquer arquivo `.uc` diretamente no compilador oficial de referência:
```bash
java -cp "tools;tools/uc-compilador.jar" RefCompiler examples/decl.uc
```
