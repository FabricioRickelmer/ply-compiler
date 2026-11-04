import glob
import os
import subprocess
import sys

esperados = {
    'undeclared_var.uc': 'nao declarada',
    'redeclared_var.uc': 'redeclarada',
    'type_mismatch.uc': 'incompatíveis',
    'break_outside_loop.uc': 'break fora',
    'comentario_nao_fechado.uc': 'comentário não fechado',
    'expoente_sem_digitos.uc': 'expoente sem dígitos',
    'tokens_after_block.uc': 'token inesperado',
}

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
search_paths = [
    os.path.join(base_dir, 'uc-full', 'examples', 'errors', '*.uc'),
    os.path.join(base_dir, 'examples', 'errors', '*.uc')
]

error_files = []
for sp in search_paths:
    found = sorted(glob.glob(sp))
    if found:
        error_files = found
        break

compiler_py = os.path.join(base_dir, 'src', 'lab2_semantica.py')

ok = 0
print("=== BATERIA DE TESTES DE ERROS (LABORATÓRIO 2 - SEÇÃO 6.1) ===")
for arq in error_files:
    nome = os.path.basename(arq)
    if nome not in esperados:
        continue
    my_env = os.environ.copy()
    my_env['PYTHONIOENCODING'] = 'utf-8'
    r = subprocess.run([sys.executable, compiler_py, arq],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', env=my_env)
    out = (r.stdout or '') + (r.stderr or '')
    if esperados[nome] in out:
        print(f"OK {nome}")
        ok += 1
    else:
        print(f"FALHOU {nome}")
        print("  Saida obtida:\n", out)

print(f"\nResultado final: {ok}/{len(esperados)}")
if ok == len(esperados):
    print("Sucesso! Todos os 7 casos de erro foram detectados corretamente.")
    sys.exit(0)
else:
    print("Atencao: Alguns testes falharam.")
    sys.exit(1)
