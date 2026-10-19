import os
import sys
import ply.lex as lex
import ply.yacc as yacc

# Estado global do compilador
SYMBOLS = {}
OFFSET = 0
LABEL_COUNT = 0
IF_PENDING = []
WHILE_PENDING = []
DO_PENDING = []
LOOP_EXITS = []

def new_label():
    global LABEL_COUNT
    LABEL_COUNT += 1
    return LABEL_COUNT

def emit(instrucao):
    print(instrucao)

def reset_compiler():
    global SYMBOLS, OFFSET, LABEL_COUNT, IF_PENDING, WHILE_PENDING, DO_PENDING, LOOP_EXITS
    SYMBOLS = {}
    OFFSET = 0
    LABEL_COUNT = 0
    IF_PENDING = []
    WHILE_PENDING = []
    DO_PENDING = []
    LOOP_EXITS = []

# Analisador lexico
reserved = {
    'if': 'IF',
    'else': 'ELSE',
    'while': 'WHILE',
    'do': 'DO',
    'break': 'BREAK',
    'print': 'PRINT',
    'read': 'READ',
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
    'PLUS', 'MINUS', 'TIMES', 'DIVI',
] + list(reserved.values())

literals = '{}();,'

# Operadores relacionais, logicos e aritmeticos
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

# Descarte de espacos e tabulacoes
t_ignore = ' \t'

# Tratamento de comentarios
def t_COMMENT_SINGLE(t):
    r'//.*'
    pass

def t_COMMENT_BLOCK(t):
    r'/\*(.|\n)*?\*/'
    t.lexer.lineno += t.value.count('\n')

# Numeros reais e inteiros
def t_REAL(t):
    r'\d+\.\d+'
    t.value = float(t.value)
    return t

def t_NUM(t):
    r'\d+'
    t.value = int(t.value)
    return t

# Identificadores e palavras reservadas
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    print(f"caractere ilegal {t.value[0]!r} na linha {t.lexer.lineno}")
    t.lexer.skip(1)

lexer = lex.lex()

# Analisador sintatico e traducao dirigida por sintaxe
start = 'program'

# Estrutura do programa e blocos de comandos
def p_program(p):
    """program : opt_stmts"""
    p[0] = p[1]

def p_opt_stmts(p):
    """opt_stmts : stmts
                 | empty"""
    p[0] = p[1] if len(p) == 2 else None

def p_stmts(p):
    """stmts : stmts stmt
             | stmt"""
    pass

def p_stmt_block(p):
    """stmt : '{' opt_stmts '}'"""
    pass

# Declaracoes de variaveis
def p_decl(p):
    """stmt : INT ID ';'
            | FLOAT ID ';'"""
    global OFFSET
    tipo = p[1]
    nome = p[2]
    if nome in SYMBOLS:
        print(f"linha {p.lineno(2)}: variavel '{nome}' ja declarada")
        raise SystemExit(1)
    SYMBOLS[nome] = OFFSET
    largura = 4 if tipo == 'int' else 8
    emit(f"AMEM {largura}\t; {nome} address: {OFFSET}")
    OFFSET += largura

# Atribuicao
def p_stmt_assign(p):
    """stmt : ID ASSIGN bool ';'"""
    if p[1] not in SYMBOLS:
        print(f"linha {p.lineno(1)}: variavel nao declarada")
        raise SystemExit(1)
    emit(f"ARMZ 0,{SYMBOLS[p[1]]}\t; {p[1]}")

# Comandos de entrada e saida
def p_stmt_print(p):
    """stmt : PRINT '(' bool ')' ';'"""
    emit("IMPR")

def p_stmt_read(p):
    """stmt : READ '(' ID ')' ';'"""
    if p[3] not in SYMBOLS:
        print(f"linha {p.lineno(3)}: variavel nao declarada")
        raise SystemExit(1)
    emit("LEIT")
    emit(f"ARMZ 0,{SYMBOLS[p[3]]}\t; {p[3]}")

# Comando condicional if e else
def p_if_head(p):
    """if_head : IF '(' bool ')'"""
    l1, l2 = new_label(), new_label()
    emit(f"DSVF L{l1}")
    IF_PENDING.append((l1, l2))

def p_stmt_if(p):
    """stmt : if_head stmt"""
    l1, l2 = IF_PENDING.pop()
    emit(f"L{l1}:")

def p_else_mark(p):
    """else_mark : """
    l1, l2 = IF_PENDING[-1]
    emit(f"DSVS L{l2}")
    emit(f"L{l1}:")

def p_stmt_if_else(p):
    """stmt : if_head stmt ELSE else_mark stmt"""
    emit(f"L{IF_PENDING.pop()[1]}:")

# Comando de repeticao while e interrupcao break
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

def p_stmt_break(p):
    """stmt : BREAK ';'"""
    if not LOOP_EXITS:
        print(f"linha {p.lineno(1)}: break fora de um laco")
        raise SystemExit(1)
    emit(f"DSVS L{LOOP_EXITS[-1]}\t; break")

# Comando de repeticao pos-testado do-while
def p_do_start(p):
    """do_start : """
    l1 = new_label()
    l2 = new_label()
    emit(f"L{l1}:")
    DO_PENDING.append((l1, l2))
    LOOP_EXITS.append(l2)

def p_stmt_do_while(p):
    """stmt : DO do_start stmt WHILE '(' bool ')' ';'"""
    l1, l2 = DO_PENDING.pop()
    LOOP_EXITS.pop()
    emit(f"DSVT L{l1}")
    emit(f"L{l2}:")

# Hierarquia de expressoes por precedencia
def p_bool_or(p):
    """bool : bool OR join"""
    emit("DISJ")
    p[0] = p[1]

def p_bool_join(p):
    """bool : join"""
    p[0] = p[1]

def p_join_and(p):
    """join : join AND equality"""
    emit("CONJ")
    p[0] = p[1]

def p_join_equality(p):
    """join : equality"""
    p[0] = p[1]

def p_equality_eq(p):
    """equality : equality EQ rel"""
    emit("CMIG")
    p[0] = p[1]

def p_equality_ne(p):
    """equality : equality NE rel"""
    emit("CMDG")
    p[0] = p[1]

def p_equality_rel(p):
    """equality : rel"""
    p[0] = p[1]

def p_rel_lt(p):
    """rel : expr LT expr"""
    emit("CMME")
    p[0] = p[1]

def p_rel_le(p):
    """rel : expr LE expr"""
    emit("CMEG")
    p[0] = p[1]

def p_rel_gt(p):
    """rel : expr GT expr"""
    emit("CMMA")
    p[0] = p[1]

def p_rel_ge(p):
    """rel : expr GE expr"""
    emit("CMAG")
    p[0] = p[1]

def p_rel_expr(p):
    """rel : expr"""
    p[0] = p[1]

def p_expr_plus(p):
    """expr : expr PLUS term"""
    emit("SOMA")
    p[0] = p[1]

def p_expr_minus(p):
    """expr : expr MINUS term"""
    emit("SUBT")
    p[0] = p[1]

def p_expr_term(p):
    """expr : term"""
    p[0] = p[1]

def p_term_times(p):
    """term : term TIMES unary"""
    emit("MULT")
    p[0] = p[1]

def p_term_divi(p):
    """term : term DIVI unary"""
    emit("DIVI")
    p[0] = p[1]

def p_term_unary(p):
    """term : unary"""
    p[0] = p[1]

def p_unary_not(p):
    """unary : NOT unary"""
    emit("NEGA")
    p[0] = p[1]

def p_unary_minus(p):
    """unary : MINUS unary"""
    emit("INVR")
    p[0] = p[1]

def p_unary_factor(p):
    """unary : factor"""
    p[0] = p[1]

def p_factor_group(p):
    """factor : '(' bool ')'"""
    p[0] = p[2]

def p_factor_num(p):
    """factor : NUM"""
    emit(f"CRCT {p[1]}")
    p[0] = p[1]

def p_factor_real(p):
    """factor : REAL"""
    emit(f"CRCT {p[1]}")
    p[0] = p[1]

def p_factor_true(p):
    """factor : TRUE"""
    emit("CRCT 1")
    p[0] = 1

def p_factor_false(p):
    """factor : FALSE"""
    emit("CRCT 0")
    p[0] = 0

def p_factor_id(p):
    """factor : ID"""
    if p[1] not in SYMBOLS:
        print(f"linha {p.lineno(1)}: variavel nao declarada")
        raise SystemExit(1)
    emit(f"CRVL 0,{SYMBOLS[p[1]]}\t; {p[1]}")
    p[0] = p[1]

def p_empty(p):
    """empty :"""
    pass

def p_error(p):
    if p:
        print(f"Erro de sintaxe na linha {p.lineno}: token inesperado '{p.value}'")
    else:
        print("Erro de sintaxe: fim de arquivo inesperado")
    raise SystemExit(1)

# Geracao do parser LALR
parser = yacc.yacc(outputdir=os.path.dirname(os.path.abspath(__file__)))

# Execucao por linha de comando
if __name__ == '__main__':
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        parser.parse(code, lexer=lexer)
    else:
        print("Uso: python src/lab1_tds.py <arquivo.uc>")
