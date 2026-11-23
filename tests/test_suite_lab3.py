"""
Suíte de Testes Automatizada — Laboratório 3: Geração de Código com Backpatching
Disciplina: ECOI2219 — Compiladores (UNIFEI - Campus Itabira)
Professor: Prof. Walter Aoiama Nagai
"""

import os
import sys
import glob
import tempfile
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPILER = os.path.join(BASE_DIR, 'src', 'lab3_gerador.py')
MEPA = os.path.join(BASE_DIR, 'mepa', 'mepa_pt.py')

my_env = os.environ.copy()
my_env['PYTHONIOENCODING'] = 'utf-8'

print("=====================================================================")
print("     BATERIA DE TESTES INTEGRADA — LABORATÓRIO 3 (BACKPATCHING)     ")
print("=====================================================================\n")

# PARTE 1: PROGRAMAS VÁLIDOS (EXECUÇÃO NA MEPA 5.0)
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
        print(f"  [PULADO] {rel_path} não encontrado")
        continue

    # Compilar com lab3_gerador.py
    res_comp = subprocess.run([sys.executable, COMPILER, abs_path],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', env=my_env)
    if res_comp.returncode != 0:
        print(f"  [FALHA NA COMPILAÇÃO] {rel_path}:\n{res_comp.stderr}")
        continue

    mepa_code = res_comp.stdout
    tmp = tempfile.NamedTemporaryFile('w', suffix='.mepa', delete=False, encoding='utf-8')
    tmp.write(mepa_code)
    tmp.close()

    res_mepa = subprocess.run([sys.executable, MEPA, '--progfile', tmp.name, '--silent'],
                              input=inp, capture_output=True, text=True, encoding='utf-8', errors='replace')
    os.remove(tmp.name)

    if res_mepa.returncode != 0:
        print(f"  [FALHA NO MEPA] {rel_path}:\n{res_mepa.stderr}")
        continue

    if expected_out is not None:
        actual_out = [int(float(x.strip())) for x in res_mepa.stdout.strip().splitlines() if x.strip()]
        if actual_out != expected_out:
            print(f"  [SAÍDA DIVERGENTE] {rel_path}: esperado {expected_out}, obtido {actual_out}")
            continue

    print(f"  [OK] {rel_path}")
    valid_ok += 1

print(f"\nTotal válidos aprovados: {valid_ok}/{len(VALID_CASES)}\n")

# PARTE 2: TESTE INTEGRADOR — FIBONACCI (SEÇÃO 6)
print("--- PARTE 2: TESTE INTEGRADOR — FIBONACCI (ENTRADAS 1, 10, 20) ---")
fib_cases = [
    ("1\n", [1, 1]),
    ("10\n", [10, 55]),
    ("20\n", [20, 6765]),
]
fib_path = os.path.join(BASE_DIR, 'examples', 'fib.uc')
res_fib_comp = subprocess.run([sys.executable, COMPILER, fib_path],
                              capture_output=True, text=True, encoding='utf-8', errors='replace', env=my_env)
fib_ok = 0
if res_fib_comp.returncode == 0:
    tmp = tempfile.NamedTemporaryFile('w', suffix='.mepa', delete=False, encoding='utf-8')
    tmp.write(res_fib_comp.stdout)
    tmp.close()
    for inp_val, exp_vals in fib_cases:
        r = subprocess.run([sys.executable, MEPA, '--progfile', tmp.name, '--silent'],
                           input=inp_val, capture_output=True, text=True, encoding='utf-8', errors='replace')
        out_vals = [int(float(x.strip())) for x in r.stdout.strip().splitlines() if x.strip()]
        if out_vals == exp_vals:
            print(f"  [OK FIB] Entrada {inp_val.strip()} -> Saída {out_vals}")
            fib_ok += 1
        else:
            print(f"  [FALHA FIB] Entrada {inp_val.strip()}: esperado {exp_vals}, obtido {out_vals}")
    os.remove(tmp.name)
else:
    print(f"  [FALHA] Não foi possível compilar {fib_path}")

print(f"\nTotal Fibonacci aprovados: {fib_ok}/{len(fib_cases)}\n")

# PARTE 3: DESAFIOS ESPECÍFICOS (DESAFIOS 5.1, 5.2 E 5.3)
print("--- PARTE 3: TESTES DOS DESAFIOS DO ROTEIRO ---")
desafios_ok = 0

# Desafio 5.2: while s <= n (s=1, n=100 -> 256)
d52_code = """{
    int s; int n; read(s); read(n);
    while (s <= n) s = s + 3 * s;
    print(s);
}"""
tmp_uc = tempfile.NamedTemporaryFile('w', suffix='.uc', delete=False, encoding='utf-8')
tmp_uc.write(d52_code)
tmp_uc.close()
r_comp = subprocess.run([sys.executable, COMPILER, tmp_uc.name],
                        capture_output=True, text=True, encoding='utf-8', errors='replace', env=my_env)
os.remove(tmp_uc.name)
if r_comp.returncode == 0:
    tmp_mepa = tempfile.NamedTemporaryFile('w', suffix='.mepa', delete=False, encoding='utf-8')
    tmp_mepa.write(r_comp.stdout)
    tmp_mepa.close()
    r_mepa = subprocess.run([sys.executable, MEPA, '--progfile', tmp_mepa.name, '--silent'],
                            input="1\n100\n", capture_output=True, text=True, encoding='utf-8', errors='replace')
    os.remove(tmp_mepa.name)
    val = [int(float(x.strip())) for x in r_mepa.stdout.strip().splitlines() if x.strip()]
    if val == [256]:
        print("  [OK] Desafio 5.2: while sem chaves (s=1, n=100) -> 256")
        desafios_ok += 1
    else:
        print(f"  [FALHA] Desafio 5.2: esperado [256], obtido {val}")

# Desafio 5.3: dois breaks no mesmo laço
d53_code = """{
    int i;
    i = 0;
    while (i < 10) {
        i = i + 1;
        if (i == 3) break;
        if (i == 5) break;
    }
    print(i);
}"""
tmp_uc = tempfile.NamedTemporaryFile('w', suffix='.uc', delete=False, encoding='utf-8')
tmp_uc.write(d53_code)
tmp_uc.close()
r_comp = subprocess.run([sys.executable, COMPILER, tmp_uc.name],
                        capture_output=True, text=True, encoding='utf-8', errors='replace', env=my_env)
os.remove(tmp_uc.name)
if r_comp.returncode == 0:
    tmp_mepa = tempfile.NamedTemporaryFile('w', suffix='.mepa', delete=False, encoding='utf-8')
    tmp_mepa.write(r_comp.stdout)
    tmp_mepa.close()
    r_mepa = subprocess.run([sys.executable, MEPA, '--progfile', tmp_mepa.name, '--silent'],
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    os.remove(tmp_mepa.name)
    val = [int(float(x.strip())) for x in r_mepa.stdout.strip().splitlines() if x.strip()]
    if val == [3]:
        print("  [OK] Desafio 5.3: Laço com dois breaks remendados corretamente -> 3")
        desafios_ok += 1
    else:
        print(f"  [FALHA] Desafio 5.3: esperado [3], obtido {val}")

# Desafio Seção 2.3: Blocos aninhados e deslocamento de memória
d23_code = """{
    int x; x = 1;
    {
        int y; y = x + 1;
        print(y);
    }
    print(x);
}"""
tmp_uc = tempfile.NamedTemporaryFile('w', suffix='.uc', delete=False, encoding='utf-8')
tmp_uc.write(d23_code)
tmp_uc.close()
r_comp = subprocess.run([sys.executable, COMPILER, tmp_uc.name],
                        capture_output=True, text=True, encoding='utf-8', errors='replace', env=my_env)
os.remove(tmp_uc.name)
if r_comp.returncode == 0:
    tmp_mepa = tempfile.NamedTemporaryFile('w', suffix='.mepa', delete=False, encoding='utf-8')
    tmp_mepa.write(r_comp.stdout)
    tmp_mepa.close()
    r_mepa = subprocess.run([sys.executable, MEPA, '--progfile', tmp_mepa.name, '--silent'],
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    os.remove(tmp_mepa.name)
    val = [int(float(x.strip())) for x in r_mepa.stdout.strip().splitlines() if x.strip()]
    if val == [2, 1]:
        print("  [OK] Seção 2.3: Blocos aninhados (offset contínuo) -> [2, 1]")
        desafios_ok += 1
    else:
        print(f"  [FALHA] Seção 2.3: esperado [2, 1], obtido {val}")

# Checklist Seção 5: do-while executando ao menos uma vez com condição falsa
ddo_code = """{
    int x; x = 99;
    do {
        print(x);
    } while (false);
}"""
tmp_uc = tempfile.NamedTemporaryFile('w', suffix='.uc', delete=False, encoding='utf-8')
tmp_uc.write(ddo_code)
tmp_uc.close()
r_comp = subprocess.run([sys.executable, COMPILER, tmp_uc.name],
                        capture_output=True, text=True, encoding='utf-8', errors='replace', env=my_env)
os.remove(tmp_uc.name)
if r_comp.returncode == 0:
    tmp_mepa = tempfile.NamedTemporaryFile('w', suffix='.mepa', delete=False, encoding='utf-8')
    tmp_mepa.write(r_comp.stdout)
    tmp_mepa.close()
    r_mepa = subprocess.run([sys.executable, MEPA, '--progfile', tmp_mepa.name, '--silent'],
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    os.remove(tmp_mepa.name)
    val = [int(float(x.strip())) for x in r_mepa.stdout.strip().splitlines() if x.strip()]
    if val == [99]:
        print("  [OK] Seção 5: do-while com condição falsa na entrada executa 1x -> [99]")
        desafios_ok += 1
    else:
        print(f"  [FALHA] Seção 5: esperado [99], obtido {val}")

print(f"\nTotal Desafios aprovados: {desafios_ok}/4\n")

# PARTE 4: BATERIA OFICIAL DE ERROS (7 CASOS)
ERROR_EXPECTED = {
    'undeclared_var.uc': 'nao declarada',
    'redeclared_var.uc': 'redeclarada',
    'type_mismatch.uc': 'incompatíveis',
    'break_outside_loop.uc': 'break fora',
    'comentario_nao_fechado.uc': 'comentário não fechado',
    'expoente_sem_digitos.uc': 'expoente sem dígitos',
    'tokens_after_block.uc': 'token inesperado',
}

print("--- PARTE 4: BATERIA DE ERROS ESPERADOS (7 CASOS) ---")
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

if valid_ok == len(VALID_CASES) and fib_ok == len(fib_cases) and desafios_ok == 4 and error_ok == len(ERROR_EXPECTED):
    print("=====================================================================")
    print("        TODOS OS TESTES DO LAB 3 PASSARAM COM 100% DE SUCESSO!       ")
    print("=====================================================================")
    sys.exit(0)
else:
    print("ATENÇÃO: Houve falhas nos testes do Lab 3.")
    sys.exit(1)
