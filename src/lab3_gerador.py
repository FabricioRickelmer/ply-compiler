"""
Compilador uC — Laboratorio 3: Geracao de Codigo (MVP) com PLY e Backpatching
Disciplina: ECOI2219 — Compiladores (UNIFEI - Campus Itabira)
Professor: Prof. Walter Aoiama Nagai

Este modulo estende a analise semantica do Laboratorio 2 com geracao de codigo
dirigida por sintaxe utilizando listas de pendencias (backpatching) para a
resolucao de desvios para frente (if, if-else, while, do-while e break).
"""

import os
import sys
import re
import ply.lex as lex
import ply.yacc as yacc

# =====================================================================
# 1. SISTEMA DE TIPOS DO uC (Secao 2 do Roteiro)
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
# 2. TABELA DE SIMBOLOS E AMBIENTES (ESCOPOS)
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
# 3. INFRAESTRUTURA DE GERACAO DE CODIGO E BACKPATCHING (Secao 3)
# =====================================================================

CODE = []
PENDING_LABELS = []
LABEL_COUNT = 0
GLOBAL_OFFSET = 0
TOP = Env(None)
BLOCK_STACK = []
WHILES = []
IFS = []


def new_label():
    """Gera um rotulo simbolico unico (L1, L2, L3, ...)."""
    global LABEL_COUNT
    LABEL_COUNT += 1
    return f"L{LABEL_COUNT}"


def emit(op_or_instr, arg=None, comment=""):
    """
    Emite uma instrucao definida para o buffer de codigo CODE.
    Prefixa automaticamente quaisquer rotulos pendentes em PENDING_LABELS.
    """
    global PENDING_LABELS
    if arg is None and ' ' in op_or_instr:
        parts = op_or_instr.split(None, 1)
        op = parts[0]
        arg = parts[1]
    else:
        op = op_or_instr

    item = {
        'op': op,
        'arg': arg,
        'labels': list(PENDING_LABELS),
        'comment': comment
    }
    PENDING_LABELS.clear()
    CODE.append(item)
    return len(CODE) - 1


def emit_marked(op, comment=""):
    """
    Emite instrucao com argumento de desvio pendente (None);
    devolve o indice no buffer de codigo CODE para posterior backpatching.
    Implementa a correcao auditada do Desafio 5.3 (retorna len(CODE) - 1).
    """
    global PENDING_LABELS
    item = {
        'op': op,
        'arg': None,
        'labels': list(PENDING_LABELS),
        'comment': comment
    }
    PENDING_LABELS.clear()
    CODE.append(item)
    return len(CODE) - 1


def patch(idx, label):
    """
    Remenda a instrucao na posicao idx com o rotulo de destino especificado.
    Inclui protecao contra sobrescrita indevida (Desafio 5.3).
    """
    if idx < 0 or idx >= len(CODE):
        raise IndexError(f"Indice de remendo invalido no buffer CODE: {idx}")
    if CODE[idx]['arg'] is not None and CODE[idx]['arg'] != label:
        raise ValueError(
            f"Tentativa de sobrescrever remendo em CODE[{idx}]: "
            f"ja era '{CODE[idx]['arg']}', novo: '{label}'"
        )
    CODE[idx]['arg'] = label


def backpatch(lst, label):
    """Remenda todas as referencias de desvios pendentes contidas em uma lista."""
    for idx in lst:
        patch(idx, label)


def emit_here(label):
    """
    Registra um rotulo para ser prefixado a proxima instrucao emitida.
    Garante conformidade com o MEPA 5.0 (rotulo e instrucao na mesma linha).
    """
    PENDING_LABELS.append(label)


def err(msg):
    """Emite mensagem de erro e encerra com codigo de retorno 1."""
    print(msg, file=sys.stderr)
    print(msg)
    sys.exit(1)


def reset_compiler():
    """Reinicia o estado global do compilador para novas execucoes."""
    global CODE, PENDING_LABELS, LABEL_COUNT, GLOBAL_OFFSET, TOP, BLOCK_STACK, WHILES, IFS
    CODE = []
    PENDING_LABELS = []
    LABEL_COUNT = 0
    GLOBAL_OFFSET = 0
    TOP = Env(None)
    BLOCK_STACK = []
    WHILES = []
    IFS = []


def format_code():
    """Formata o buffer de instrucoes CODE no formato aceito pelo MEPA 5.0."""
    global PENDING_LABELS
    # Se restou algum rotulo apos PARA, anexa como NADA
    if PENDING_LABELS:
        CODE.append({
            'op': 'NADA',
            'arg': None,
            'labels': list(PENDING_LABELS),
            'comment': 'rotulo final'
        })
        PENDING_LABELS.clear()

    lines = []
    for item in CODE:
        prefix = ""
        if item['labels']:
            prefix = " ".join(f"{lbl}:" for lbl in item['labels']) + " "
        op_str = item['op']
        arg_str = f" {item['arg']}" if item['arg'] is not None else ""
        comment_str = f"\t; {item['comment']}" if item['comment'] else ""
        lines.append(f"{prefix}{op_str}{arg_str}{comment_str}")
    return "\n".join(lines)


# =====================================================================
# 4. ANALISADOR LEXICO (PLY Lex)
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
# 5. ANALISADOR SINTATICO E SINTESE COM BACKPATCHING (PLY Yacc)
# =====================================================================

start = 'program'

# Forma de todo programa: INPP, comandos, DMEM, PARA
def p_program(p):
    """program : program_start block"""
    emit("PARA")
    p[0] = p[2]


def p_program_start(p):
    """program_start : """
    emit("INPP")


def p_block_start(p):
    """block_start : '{'"""
    global TOP
    TOP = Env(prev=TOP)
    BLOCK_STACK.append({'env': TOP, 'prev_top': TOP.prev})
    p[0] = TOP


def p_block(p):
    """block : block_start opt_stmts '}'"""
    global TOP
    ctx = BLOCK_STACK.pop()
    # Se o bloco alocou variaveis locais, devolve com DMEM (Secao 2.3)
    if ctx['env'].usage > 0:
        emit(f"DMEM {ctx['env'].usage}")
    TOP = ctx['prev_top']
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


# Declaracoes de variaveis
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
        emit(f"AMEM {var_type.width}", comment=f"{name} address: {GLOBAL_OFFSET}")
        GLOBAL_OFFSET += var_type.width


# Atribuicao com verificacao de compatibilidade de tipos
def p_stmt_assign(p):
    """stmt : ID ASSIGN bool ';'"""
    name = p[1]
    id_ = TOP.get(name)
    if id_ is None:
        err(f"linha {p.lineno(1)}: variável não declarada (nao declarada)")
    expr_type = p[3]
    if is_numeric(id_.type) and is_numeric(expr_type):
        pass  # Coercao numerica permitida
    elif id_.type.matches(expr_type):
        pass  # Equivalencia estrutural
    else:
        err(f"linha {p.lineno(1)}: erro semântico: tipos {id_.type} e {expr_type} são incompatíveis")
    emit(f"ARMZ 0,{id_.offset}", comment=name)


# Comandos de Entrada e Saida
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
    emit(f"ARMZ 0,{id_.offset}", comment=name)


# Comandos Condicionais com Backpatching (Secao 4.1 e 4.2)
def p_if_head(p):
    """if_head : IF '(' bool ')'"""
    cond_type = p[3]
    if cond_type != Type.Bool:
        err(f"linha {p.lineno(1)}: erro semântico: a expressão não tem valor booleano.")
    # Emite DSVF com rotulo pendente de remendo para o falso
    idx = emit_marked("DSVF")
    IFS.append({'falses': [idx], 'exits': []})


def p_stmt_if(p):
    """stmt : if_head stmt"""
    l1 = new_label()
    emit_here(l1)
    info = IFS.pop()
    backpatch(info['falses'], l1)


def p_if_else_head(p):
    """if_else_head : if_head stmt ELSE"""
    l1 = new_label()
    emit_here(l1)  # Inicio do ramo else
    backpatch(IFS[-1]['falses'], l1)  # Remenda o DSVF da condicao para L1
    idx = emit_marked("DSVS")  # Desvio pendente ao fim do then para pular o else
    IFS[-1]['exits'] = [idx]


def p_stmt_if_else(p):
    """stmt : if_else_head stmt"""
    l2 = new_label()
    emit_here(l2)  # Saida apos o else
    info = IFS.pop()
    backpatch(info['exits'], l2)


# Lacos de Repeticao com Backpatching (Secao 3.3, 4.3 e 4.4)
def p_while_start(p):
    """while_start : """
    l1 = new_label()
    emit_here(l1)  # O rotulo de inicio JA existe no teste
    WHILES.append({'begin': l1, 'exits': []})


def p_while_head(p):
    """while_head : WHILE '(' while_start bool ')'"""
    cond_type = p[4]
    if cond_type != Type.Bool:
        err(f"linha {p.lineno(1)}: erro semântico: a expressão não tem valor booleano.")
    idx = emit_marked("DSVF")  # Desvio pendente para saida do laco
    WHILES[-1]['exits'].append(idx)


def p_stmt_while(p):
    """stmt : while_head stmt"""
    w = WHILES.pop()
    emit(f"DSVS {w['begin']}")  # Volta incondicional ao teste
    l2 = new_label()
    emit_here(l2)
    backpatch(w['exits'], l2)  # Remenda DSVF da condicao e todos os breaks do laco


def p_do_start(p):
    """do_start : """
    l1 = new_label()
    emit_here(l1)
    WHILES.append({'begin': l1, 'exits': []})


def p_stmt_do(p):
    """stmt : DO do_start stmt WHILE '(' bool ')' ';'"""
    cond_type = p[6]
    if cond_type != Type.Bool:
        err(f"linha {p.lineno(4)}: erro semântico: a expressão não tem valor booleano.")
    w = WHILES.pop()
    l2 = new_label()
    # Em do-while: se a condicao for falsa, desvia para L2 (saida); se verdadeira, volta a L1
    emit(f"DSVF {l2}")
    emit(f"DSVS {w['begin']}")
    emit_here(l2)
    if w['exits']:
        backpatch(w['exits'], l2)  # Remenda breaks ocorridos dentro do do-while


def p_stmt_break(p):
    """stmt : BREAK ';'"""
    if not WHILES:
        err(f"linha {p.lineno(1)}: erro semântico: break fora de um laço")
    idx = emit_marked("DSVS", comment="break")
    WHILES[-1]['exits'].append(idx)


# =====================================================================
# 6. CASCATA COMPLETA DE EXPRESSOES E SINTESE DE TIPOS (Secao 2)
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
        pass
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
    emit(f"CRVL 0,{id_.offset}", comment=name)
    p[0] = id_.type


def p_empty(p):
    """empty :"""
    pass


def p_error(p):
    if p:
        err(f"linha {p.lineno}: erro de sintaxe: token inesperado '{p.value}' após o fim do programa")
    else:
        err("erro de sintaxe: fim de arquivo inesperado")


# Geracao do parser LALR com PLY
parser = yacc.yacc(outputdir=os.path.dirname(os.path.abspath(__file__)))


def compile_uc(source_code):
    """Compila o codigo fonte uC e retorna a listagem de instrucoes MEPA 5.0."""
    reset_compiler()
    parser.parse(source_code, lexer=lexer)
    return format_code()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        mepa_code = compile_uc(code)
        print(mepa_code)
    else:
        print("Uso: python src/lab3_gerador.py <arquivo.uc>")
