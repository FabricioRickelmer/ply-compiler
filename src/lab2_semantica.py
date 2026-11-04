import os
import sys
import re
import ply.lex as lex
import ply.yacc as yacc

# =====================================================================
# SISTEMA DE TIPOS DO uC (Secao 2 do Roteiro)
# =====================================================================

class Type:
    """Classe base para representacao de tipos do uC."""
    def __init__(self, name, width, numeric=False):
        self.name = name
        self.width = width
        self.numeric = numeric

    def matches(self, other):
        """Para tipos basicos, comparacao por igualdade (singletons)."""
        return self == other

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


# Singletons dos tipos primitivos
Type.Int   = Type("int", 4, numeric=True)
Type.Float = Type("float", 8, numeric=True)
Type.Char  = Type("char", 1, numeric=True)
Type.Bool  = Type("bool", 1, numeric=False)


class Array(Type):
    """Representacao de arranjos com equivalencia estrutural recursiva."""
    def __init__(self, of, size):
        super().__init__(f"{of}[{size}]", size * of.width, numeric=False)
        self.of = of
        self.size = size

    def matches(self, other):
        return (isinstance(other, Array) and self.size == other.size
                and self.of.matches(other.of))


class Pointer(Type):
    """Representacao de ponteiros com equivalencia estrutural recursiva."""
    def __init__(self, of):
        super().__init__(f"*{of}", 4, numeric=False)
        self.of = of

    def matches(self, other):
        return isinstance(other, Pointer) and self.of.matches(other.of)


def is_numeric(t):
    """Verifica se o tipo participa de operacoes aritmeticas (int, float, char)."""
    return getattr(t, 'numeric', False)


def max_type(t1, t2):
    """
    Funcao de coercao / tipo mais abrangente para operacoes aritmeticas.
    Retorna None se algum dos operandos nao for numerico.
    """
    if not (is_numeric(t1) and is_numeric(t2)):
        return None
    if t1 == Type.Float or t2 == Type.Float:
        return Type.Float
    if t1 == Type.Int or t2 == Type.Int:
        return Type.Int
    return Type.Char


# =====================================================================
# TABELA DE SIMBOLOS E ESCOPOS (Secao 3 do Roteiro)
# =====================================================================

class Id:
    """Informacoes armazenadas para cada simbolo: nome, tipo e deslocamento."""
    def __init__(self, name, type_, offset):
        self.name = name
        self.type = type_
        self.offset = offset

    def __repr__(self):
        return f"{self.name}:{self.type}@{self.offset}"


class Env:
    """
    Ambiente encadeado para suporte a escopos aninhados (lista ligada).
    Cada bloco cria um novo ambiente cujo ponteiro 'prev' aponta para o externo.
    """
    def __init__(self, prev=None):
        self.table = {}
        self.prev = prev
        self.usage = 0

    def put(self, name, id_):
        if name in self.table:
            return False
        self.table[name] = id_
        self.usage += id_.type.width
        return True

    def get(self, name):
        env = self
        while env is not None:
            if name in env.table:
                return env.table[name]
            env = env.prev
        return None


# =====================================================================
# ESTADO GLOBAL DO COMPILADOR
# =====================================================================

GLOBAL_OFFSET = 0
LABEL_COUNT = 0
TOP = Env(None)
IF_PENDING = []
WHILE_PENDING = []
DO_PENDING = []
LOOP_EXITS = []

def new_label():
    global LABEL_COUNT
    LABEL_COUNT += 1
    return LABEL_COUNT

def emit(instr):
    print(instr)

def err(msg):
    """Emite mensagem de erro e aborta com codigo 1."""
    print(msg, file=sys.stderr)
    print(msg)
    sys.exit(1)

def reset_compiler():
    global GLOBAL_OFFSET, LABEL_COUNT, TOP, IF_PENDING, WHILE_PENDING, DO_PENDING, LOOP_EXITS
    GLOBAL_OFFSET = 0
    LABEL_COUNT = 0
    TOP = Env(None)
    IF_PENDING = []
    WHILE_PENDING = []
    DO_PENDING = []
    LOOP_EXITS = []


# =====================================================================
# ANALISADOR LEXICO (PLY Lex)
# =====================================================================

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
    'char': 'CHAR',
    'bool': 'BOOL',
}

tokens = [
    'ID', 'NUM', 'REAL', 'CHARLIT',
    'EQ', 'NE', 'LE', 'GE',
    'AND', 'OR', 'NOT',
    'LT', 'GT', 'ASSIGN',
    'PLUS', 'MINUS', 'TIMES', 'DIVI',
] + list(reserved.values())

literals = '{}();,'

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

t_ignore = ' \t'

def t_COMMENT_SINGLE(t):
    r'//.*'
    pass

def t_COMMENT_BLOCK(t):
    r'/\*(.|\n)*?(\*/|$)'
    if not t.value.endswith('*/'):
        err(f"linha {t.lexer.lineno}: comentário não fechado")
    t.lexer.lineno += t.value.count('\n')

def t_REAL(t):
    r'\d+\.\d+([eE][+-]?\d*)?|\d+[eE][+-]?\d*'
    val_str = t.value
    if 'e' in val_str.lower():
        parts = re.split(r'[eE]', val_str)
        exp = parts[1]
        if exp.startswith('+') or exp.startswith('-'):
            exp = exp[1:]
        if not exp:
            err(f"linha {t.lexer.lineno}: expoente sem dígitos")
    t.value = float(val_str)
    return t

def t_NUM(t):
    r'\d+'
    t.value = int(t.value)
    return t

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

def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'ID')
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    err(f"linha {t.lexer.lineno}: caractere ilegal '{t.value[0]}'")


lexer = lex.lex()


# =====================================================================
# ANALISADOR SINTATICO E SINTESE DE TIPOS (PLY Yacc)
# =====================================================================

start = 'program'

# Estrutura do Programa: todo programa uC e um bloco delimitado por { ... }
def p_program(p):
    """program : block"""
    p[0] = p[1]

def p_block_start(p):
    """block_start : '{'"""
    global TOP
    TOP = Env(prev=TOP)
    p[0] = TOP

def p_block(p):
    """block : block_start opt_stmts '}'"""
    global TOP
    TOP = TOP.prev
    p[0] = p[2]

def p_stmt_block(p):
    """stmt : block"""
    p[0] = p[1]

def p_opt_stmts(p):
    """opt_stmts : stmts
                 | empty"""
    p[0] = p[1] if len(p) == 2 else None

def p_stmts(p):
    """stmts : stmts stmt
             | stmt"""
    pass

# Tipos para declaracoes
def p_type(p):
    """type : INT
            | FLOAT
            | CHAR
            | BOOL"""
    p[0] = {
        'int': Type.Int,
        'float': Type.Float,
        'char': Type.Char,
        'bool': Type.Bool
    }[p[1]]

# Desafio 6.3: DDS de declaracoes do livro com regra recursiva a direita
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
    line = p.lineno(2) or p.lexer.lineno
    for name in p[2]:
        if not TOP.put(name, Id(name, var_type, GLOBAL_OFFSET)):
            err(f"linha {line}: erro semântico: variável redeclarada {name}")
        emit(f"AMEM {var_type.width}\t; {name} address: {GLOBAL_OFFSET}")
        GLOBAL_OFFSET += var_type.width

# Atribuicao com verificacao de compatibilidade
def p_stmt_assign(p):
    """stmt : ID ASSIGN bool ';'"""
    name = p[1]
    id_ = TOP.get(name)
    if id_ is None:
        err(f"linha {p.lineno(1)}: variável não declarada (nao declarada)")
    expr_type = p[3]
    if is_numeric(id_.type) and is_numeric(expr_type):
        pass  # Coercao entre tipos numericos permitida
    elif id_.type.matches(expr_type):
        pass  # Tipos estruturalmente equivalentes
    else:
        err(f"linha {p.lineno(1)}: erro semântico: tipos {id_.type} e {expr_type} são incompatíveis")
    emit(f"ARMZ 0,{id_.offset}\t; {name}")

# Comandos de I/O
def p_stmt_print(p):
    """stmt : PRINT '(' bool ')' ';'"""
    expr_type = p[3]
    if expr_type == Type.Bool:
        err(f"linha {p.lineno(1)}: erro semântico: a expressão deveria ter valor numérico")
    emit("IMPR")

def p_stmt_read(p):
    """stmt : READ '(' ID ')' ';'"""
    name = p[3]
    id_ = TOP.get(name)
    if id_ is None:
        err(f"linha {p.lineno(3)}: variável não declarada (nao declarada)")
    emit("LEIT")
    emit(f"ARMZ 0,{id_.offset}\t; {name}")

# Condicional if e else
def p_if_head(p):
    """if_head : IF '(' bool ')'"""
    cond_type = p[3]
    if cond_type != Type.Bool:
        err(f"linha {p.lineno(1)}: erro semântico: a expressão não tem valor booleano.")
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

# Lacos de repeticao
def p_while_start(p):
    """while_start : """
    l1, l2 = new_label(), new_label()
    emit(f"L{l1}:")
    WHILE_PENDING.append((l1, l2))
    LOOP_EXITS.append(l2)

def p_while_head(p):
    """while_head : WHILE '(' while_start bool ')'"""
    cond_type = p[4]
    if cond_type != Type.Bool:
        err(f"linha {p.lineno(1)}: erro semântico: a expressão não tem valor booleano.")
    l1, l2 = WHILE_PENDING[-1]
    emit(f"DSVF L{l2}")

def p_stmt_while(p):
    """stmt : while_head stmt"""
    l1, l2 = WHILE_PENDING.pop()
    LOOP_EXITS.pop()
    emit(f"DSVS L{l1}")
    emit(f"L{l2}:")

def p_do_start(p):
    """do_start : """
    l1, l2 = new_label(), new_label()
    emit(f"L{l1}:")
    DO_PENDING.append((l1, l2))
    LOOP_EXITS.append(l2)

def p_stmt_do_while(p):
    """stmt : DO do_start stmt WHILE '(' bool ')' ';'"""
    cond_type = p[6]
    if cond_type != Type.Bool:
        err(f"linha {p.lineno(4)}: erro semântico: a expressão não tem valor booleano.")
    l1, l2 = DO_PENDING.pop()
    LOOP_EXITS.pop()
    emit(f"DSVT L{l1}")
    emit(f"L{l2}:")

def p_stmt_break(p):
    """stmt : BREAK ';'"""
    if not LOOP_EXITS:
        err(f"linha {p.lineno(1)}: erro semântico: break fora de um laço")
    emit(f"DSVS L{LOOP_EXITS[-1]}\t; break")

# =====================================================================
# CASCATA COMPLETA DE EXPRESSOES E SINTESE DE TIPOS (Secao 4)
# =====================================================================

def p_bool_or(p):
    """bool : bool OR join"""
    a, b = p[1], p[3]
    if a != Type.Bool or b != Type.Bool:
        err(f"linha {p.lineno(2)}: erro semântico: operandos de || devem ser booleanos")
    emit("DISJ")
    p[0] = Type.Bool

def p_bool_join(p):
    """bool : join"""
    p[0] = p[1]

def p_join_and(p):
    """join : join AND equality"""
    a, b = p[1], p[3]
    if a != Type.Bool or b != Type.Bool:
        err(f"linha {p.lineno(2)}: erro semântico: operandos de && devem ser booleanos")
    emit("CONJ")
    p[0] = Type.Bool

def p_join_equality(p):
    """join : equality"""
    p[0] = p[1]

def p_equality_rel(p):
    """equality : rel"""
    p[0] = p[1]

def p_equality_op(p):
    """equality : equality EQ rel
                | equality NE rel"""
    a, b = p[1], p[3]
    op = p[2]
    if is_numeric(a) and is_numeric(b):
        if max_type(a, b) is Type.Float:
            emit("CONV")  # Coercao didatica para Float
    elif a.matches(b):
        pass
    else:
        err(f"linha {p.lineno(2)}: erro semântico: tipos {a} e {b} são incompatíveis")
    emit("CMIG" if op == '==' else "CMDG")
    p[0] = Type.Bool

def p_rel_expr(p):
    """rel : expr"""
    p[0] = p[1]

def p_rel_op(p):
    """rel : expr LT expr
           | expr LE expr
           | expr GT expr
           | expr GE expr"""
    a, b = p[1], p[3]
    op = p[2]
    if not (is_numeric(a) and is_numeric(b)):
        err(f"linha {p.lineno(2)}: erro semântico: tipos {a} e {b} são incompatíveis")
    op_code = {'<': 'CMME', '<=': 'CMEG', '>': 'CMMA', '>=': 'CMAG'}[op]
    emit(op_code)
    p[0] = Type.Bool

def p_expr_term(p):
    """expr : term"""
    p[0] = p[1]

def p_expr_arith(p):
    """expr : expr PLUS term
            | expr MINUS term"""
    a, b = p[1], p[3]
    op = p[2]
    if not (is_numeric(a) and is_numeric(b)):
        err(f"linha {p.lineno(2)}: erro semântico: tipos {a} e {b} são incompatíveis")
    emit("SOMA" if op == '+' else "SUBT")
    p[0] = max_type(a, b)

def p_term_unary(p):
    """term : unary"""
    p[0] = p[1]

def p_term_arith(p):
    """term : term TIMES unary
            | term DIVI unary"""
    a, b = p[1], p[3]
    op = p[2]
    if not (is_numeric(a) and is_numeric(b)):
        err(f"linha {p.lineno(2)}: erro semântico: tipos {a} e {b} são incompatíveis")
    emit("MULT" if op == '*' else "DIVI")
    p[0] = max_type(a, b)

def p_unary_factor(p):
    """unary : factor"""
    p[0] = p[1]

def p_unary_not(p):
    """unary : NOT unary"""
    if p[2] != Type.Bool:
        err(f"linha {p.lineno(1)}: erro semântico: o tipo de dado não é booleano.")
    emit("NEGA")
    p[0] = Type.Bool

def p_unary_minus(p):
    """unary : MINUS unary"""
    if not is_numeric(p[2]):
        err(f"linha {p.lineno(1)}: erro semântico: tipos {p[2]} e {p[2]} são incompatíveis")
    emit("INVR")
    p[0] = p[2]

def p_factor_group(p):
    """factor : '(' bool ')'"""
    p[0] = p[2]

def p_factor_num(p):
    """factor : NUM"""
    emit(f"CRCT {p[1]}")
    p[0] = Type.Int

def p_factor_real(p):
    """factor : REAL"""
    emit(f"CRCT {p[1]}")
    p[0] = Type.Float

def p_factor_charlit(p):
    """factor : CHARLIT"""
    emit(f"CRCT {p[1]}")
    p[0] = Type.Char

def p_factor_true(p):
    """factor : TRUE"""
    emit("CRCT 1")
    p[0] = Type.Bool

def p_factor_false(p):
    """factor : FALSE"""
    emit("CRCT 0")
    p[0] = Type.Bool

def p_factor_id(p):
    """factor : ID"""
    name = p[1]
    id_ = TOP.get(name)
    if id_ is None:
        err(f"linha {p.lineno(1)}: variável não declarada (nao declarada)")
    emit(f"CRVL 0,{id_.offset}\t; {name}")
    p[0] = id_.type

def p_empty(p):
    """empty :"""
    pass

def p_error(p):
    if p:
        err(f"linha {p.lineno}: erro de sintaxe: token inesperado '{p.value}' após o fim do programa")
    else:
        err("erro de sintaxe: fim de arquivo inesperado")


# Geracao do parser LALR
parser = yacc.yacc(outputdir=os.path.dirname(os.path.abspath(__file__)))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        reset_compiler()
        parser.parse(code, lexer=lexer)
    else:
        print("Uso: python src/lab2_semantica.py <arquivo.uc>")
