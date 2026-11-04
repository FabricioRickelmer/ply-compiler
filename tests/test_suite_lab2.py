import os
import subprocess
import sys
import tempfile
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPILER = os.path.join(BASE_DIR, 'src', 'lab2_semantica.py')
MEPA = os.path.join(BASE_DIR, 'mepa', 'mepa_pt.py')

my_env = os.environ.copy()
my_env['PYTHONIOENCODING'] = 'utf-8'

print("=====================================================================")
print("     BATERIA DE TESTES INTEGRADA — LABORATÓRIO 2 (SEMÂNTICA)        ")
print("=====================================================================\n")

# PARTE 1: PROGRAMAS VÁLIDOS
VALID_CASES = [
    ('examples/expr.uc', None, None),
    ('examples/decl.uc', None, None),
    ('examples/precedencia.uc', None, None),
    ('examples/if.uc', None, None),
    ('examples/while.uc', None, [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]),
    ('examples/break.uc', None, [1, 2, 3, 4, 5]),
    ('examples/dowhile.uc', None, [1, 2, 3, 4, 5]),
    ('examples/fib.uc', "10\n", [10, 55]),
    ('examples/atribuicao.uc', None, [42]),
    ('examples/blocos.uc', None, [2, 1]),
    ('examples/charlit.uc', None, [98]),
    ('examples/decl_multipla.uc', None, [6]),
    ('examples/leitura.uc', "21\n", [42]),
    ('examples/logica.uc', None, [1]),
    ('examples/relacionais.uc', None, [1]),
]

print("--- PARTE 1: COMPILAÇÃO E EXECUÇÃO DE PROGRAMAS VÁLIDOS ---")
valid_ok = 0
for rel_path, inp, expected_out in VALID_CASES:
    abs_path = os.path.join(BASE_DIR, rel_path)
    if not os.path.exists(abs_path):
        print(f"[PULADO] {rel_path} não encontrado")
        continue

    # Compilar
    res_comp = subprocess.run([sys.executable, COMPILER, abs_path],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', env=my_env)
    if res_comp.returncode != 0:
        print(f"[FALHA NA COMPILAÇÃO] {rel_path}:\n{res_comp.stderr}")
        continue

    # Executar no MEPA se houver expectativa de saida
    mepa_code = res_comp.stdout
    tmp = tempfile.NamedTemporaryFile('w', suffix='.mepa', delete=False, encoding='utf-8')
    tmp.write(mepa_code)
    tmp.close()

    res_mepa = subprocess.run([sys.executable, MEPA, '--progfile', tmp.name, '--silent'],
                              input=inp, capture_output=True, text=True, encoding='utf-8', errors='replace')
    os.remove(tmp.name)

    if res_mepa.returncode != 0:
        print(f"[FALHA NO MEPA] {rel_path}:\n{res_mepa.stderr}")
        continue

    if expected_out is not None:
        actual_out = [int(float(x.strip())) for x in res_mepa.stdout.strip().splitlines() if x.strip()]
        if actual_out != expected_out:
            print(f"[SAÍDA DIVERGENTE] {rel_path}: esperado {expected_out}, obtido {actual_out}")
            continue

    print(f"  [OK] {rel_path}")
    valid_ok += 1

print(f"\nTotal válidos aprovados: {valid_ok}/{len(VALID_CASES)}\n")

# PARTE 2: BATERIA DE ERROS (SEÇÃO 6.1)
ERROR_EXPECTED = {
    'undeclared_var.uc': 'nao declarada',
    'redeclared_var.uc': 'redeclarada',
    'type_mismatch.uc': 'incompatíveis',
    'break_outside_loop.uc': 'break fora',
    'comentario_nao_fechado.uc': 'comentário não fechado',
    'expoente_sem_digitos.uc': 'expoente sem dígitos',
    'tokens_after_block.uc': 'token inesperado',
}

print("--- PARTE 2: BATERIA DE ERROS ESPERADOS (7 CASOS) ---")
error_files = sorted(glob.glob(os.path.join(BASE_DIR, 'examples', 'errors', '*.uc')))
error_ok = 0
for arq in error_files:
    nome = os.path.basename(arq)
    if nome not in ERROR_EXPECTED:
        continue
    r = subprocess.run([sys.executable, COMPILER, arq],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', env=my_env)
    out = (r.stdout or '') + (r.stderr or '')
    if ERROR_EXPECTED[nome] in out:
        print(f"  [OK REJEITADO] {nome}")
        error_ok += 1
    else:
        print(f"  [FALHOU EM REJEITAR] {nome}")
        print(f"     Saída obtida: {out}")

print(f"\nTotal erros rejeitados corretamente: {error_ok}/{len(ERROR_EXPECTED)}\n")

if valid_ok == len(VALID_CASES) and error_ok == len(ERROR_EXPECTED):
    print("=====================================================================")
    print("        TODOS OS TESTES (VÁLIDOS E ERROS) PASSARAM COM 100%!         ")
    print("=====================================================================")
    sys.exit(0)
else:
    print("ATENÇÃO: Houve falhas nos testes.")
    sys.exit(1)
