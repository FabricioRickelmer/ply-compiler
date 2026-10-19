import sys
import ply.lex as lex
import ply.yacc as yacc

# Variaveis globais
SYMBOLS = {}
OFFSET = 0
LABEL_COUNT = 0
IF_PENDING = []
WHILE_PENDING = []
LOOP_EXITS = []

def new_label():
    global LABEL_COUNT
    LABEL_COUNT += 1
    return LABEL_COUNT

def emit(instrucao):
    print(instrucao)


# Palavras reservadas
reserved = {
    'if': 'IF', 
    'else': 'ELSE', 
    'while': 'WHILE',
    'break': 'BREAK', 
    'print': 'PRINT',
    'true': 'TRUE', 
    'false': 'FALSE',
    'int': 'INT',
    'float': 'FLOAT',
}

tokens = [
    'ID', 'NUM', 'REAL', 
    'EQ', 'NE', 'LE', 'GE', 
    'AND', 'OR', 'NOT', 
    'LT', 'GT', 'ASSIGN',
    'PLUS', 'MINUS', 'TIMES', 'DIVI'
] + list(reserved.values())

# Operadores
t_EQ     = r'=='
t_NE     = r'!='
t_LE     = r'<='
t_GE     = r'>='
t_AND    = r'&&'
t_OR     = r'\|\|'
t_NOT    = r'!'
t_LT     = r'<'
t_GT     = r'>'
t_ASSIGN = r'='
t_PLUS   = r'\+'
t_MINUS  = r'-'
t_TIMES  = r'\*'
t_DIVI   = r'/'

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_NUM(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_REAL(t):
    r'\d+\.\d+'
    t.value = float(t.value)
    return t

t_ignore = ' \t\n'

def t_error(t):
    print(f"Erro lexico: {t.value[0]}")
    t.lexer.skip(1)

lexer = lex.lex()


# Precedencia de operadores
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('nonassoc', 'LT', 'GT', 'LE', 'GE', 'EQ', 'NE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVI'),
    ('right', 'NOT'),
)

# Regra vazia para marcadores
def p_empty(p):
    """empty :"""
    pass

# Estrutura do Programa
def p_program(p):
    """program : stmt_list"""
    pass

def p_stmt_list(p):
    """stmt_list : stmt_list stmt
                 | stmt"""
    pass

def p_block(p):
    """stmt : '{' stmt_list '}'
            | '{' '}'"""
    pass

# Declaracao de variaveis
def p_decl(p):
    """stmt : INT ID ';'
            | FLOAT ID ';'"""
    global OFFSET
    tipo = p[1]
    nome = p[2]
    
    if nome in SYMBOLS:
        print(f"Erro: variavel '{nome}' ja declarada")
        raise SystemExit(1)
        
    SYMBOLS[nome] = OFFSET
    largura = 4 if tipo == 'int' else 8  
    emit(f"AMEM {largura}")
    OFFSET += largura

# Atribuicao
def p_stmt_assign(p):
    """stmt : ID ASSIGN expr ';'"""
    if p[1] not in SYMBOLS:
        print(f"Erro: variavel '{p[1]}' nao declarada")
        raise SystemExit(1)
    emit(f"ARMZ 0,{SYMBOLS[p[1]]}")

# Operacoes Aritmeticas e Relacionais
def p_expr_bin(p):
    """expr : expr PLUS expr
            | expr MINUS expr
            | expr TIMES expr
            | expr DIVI expr
            | expr EQ expr
            | expr NE expr
            | expr LT expr
            | expr LE expr
            | expr GT expr
            | expr GE expr
            | expr AND expr
            | expr OR expr"""
    op = p[2]
    if op == '+': emit("SOMA")
    elif op == '-': emit("SUBTR")
    elif op == '*': emit("MULT")
    elif op == '/': emit("DIVI")
    elif op == '==': emit("CMEG")
    elif op == '!=': emit("CMDG")
    elif op == '<': emit("CMMEN")
    elif op == '<=': emit("CMEG")
    elif op == '>': emit("CMMAI")
    elif op == '>=': emit("CMAG")
    elif op == '&&': emit("CONJ")
    elif op == '||': emit("DISJ")

def p_expr_not(p):
    """expr : NOT expr"""
    emit("NEGA")

def p_expr_group(p):
    """expr : '(' expr ')'"""
    pass

def p_expr_num(p):
    """expr : NUM"""
    emit(f"CRCT {p[1]}")

def p_expr_id(p):
    """expr : ID"""
    if p[1] not in SYMBOLS:
        print(f"Erro: variavel '{p[1]}' nao declarada")
        raise SystemExit(1)
    emit(f"CRVL 0,{SYMBOLS[p[1]]}")


# Condicional (If / Else)
def p_if_head(p):
    """if_head : IF '(' expr ')'"""
    l1 = new_label()
    l2 = new_label()
    emit(f"DSVF L{l1}")
    IF_PENDING.append((l1, l2))

def p_stmt_if(p):
    """stmt : if_head stmt"""
    l1, l2 = IF_PENDING.pop()
    emit(f"L{l1}:")

def p_else_head(p):
    """else_head : ELSE"""
    l1, l2 = IF_PENDING[-1]
    emit(f"DSVS L{l2}")
    emit(f"L{l1}:")

def p_stmt_if_else(p):
    """stmt : if_head stmt else_head stmt"""
    l1, l2 = IF_PENDING.pop()
    emit(f"L{l2}:")


# Laco (While / Break)
def p_while_marker(p):
    """while_marker : empty"""
    l1 = new_label()
    l2 = new_label()
    emit(f"L{l1}:")
    WHILE_PENDING.append((l1, l2))
    LOOP_EXITS.append(l2)

def p_while_head(p):
    """while_head : WHILE while_marker '(' expr ')'"""
    l1, l2 = WHILE_PENDING[-1]
    emit(f"DSVF L{l2}")

def p_stmt_while(p):
    """stmt : while_head stmt"""
    l1, l2 = WHILE_PENDING.pop()
    LOOP_EXITS.pop()
    emit(f"DSVS L{l1}")
    emit(f"L{l2}:")

def p_stmt_break(p):
    """stmt : BREAK ';'"""
    if not LOOP_EXITS:
        print("Erro: 'break' fora de um laco")
        raise SystemExit(1)
    emit(f"DSVS L{LOOP_EXITS[-1]}")

def p_error(p):
    if p:
        print(f"Erro de sintaxe na linha {p.lineno}: token inesperado '{p.value}'")
    else:
        print("Erro de sintaxe: fim de arquivo inesperado")
    raise SystemExit(1)

parser = yacc.yacc()

# Execucao principal
if __name__ == '__main__':
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        parser.parse(code)
    else:
        print("Uso: python src/lab1_tds.py tests/teste_simples.uc")