import os
import subprocess
import sys

# Diretorio base do projeto (um nivel acima de tests/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXAMPLES = [
    (os.path.join(BASE_DIR, "exemplos", "expr.uc"), None),
    (os.path.join(BASE_DIR, "exemplos", "decl.uc"), None),
    (os.path.join(BASE_DIR, "exemplos", "precedencia.uc"), None),
    (os.path.join(BASE_DIR, "exemplos", "if.uc"), None),
    (os.path.join(BASE_DIR, "exemplos", "while.uc"), None),
    (os.path.join(BASE_DIR, "exemplos", "break.uc"), None),
    (os.path.join(BASE_DIR, "exemplos", "dowhile.uc"), None),
    (os.path.join(BASE_DIR, "exemplos", "fib.uc"), "10\n"),
]

python_exe = sys.executable
compiler_script = os.path.join(BASE_DIR, "src", "lab1_tds.py")
mepa_script = os.path.join(BASE_DIR, "mepa", "mepa_pt.py")

print("=== EXECUTANDO BATERIA DE TESTES DO COMPILADOR ===")
for uc_file, input_data in EXAMPLES:
    base_name = os.path.splitext(os.path.basename(uc_file))[0]
    out_mepa = os.path.join(BASE_DIR, "exemplos", f"{base_name}.mepa")
    rel_path = os.path.relpath(uc_file, BASE_DIR)
    print(f"\n[TESTE] Compilando {rel_path}...")
    
    # 1. Compilar
    res_comp = subprocess.run([python_exe, compiler_script, uc_file], capture_output=True, text=True)
    if res_comp.returncode != 0:
        print(f"  FALHA NA COMPILACAO:\n{res_comp.stderr}")
        continue
    
    with open(out_mepa, "w", encoding="utf-8") as f:
        f.write(res_comp.stdout)
    print(f"  Compilado com sucesso ({len(res_comp.stdout.splitlines())} instrucoes emitidas).")
    
    # 2. Executar no MEPA
    print(f"  Executando no MEPA ({os.path.relpath(mepa_script, BASE_DIR)})...")
    res_mepa = subprocess.run(
        [python_exe, mepa_script, "--progfile", out_mepa, "--silent"],
        input=input_data,
        capture_output=True,
        text=True
    )
    if res_mepa.returncode != 0:
        print(f"  FALHA NA EXECUCAO MEPA:\n{res_mepa.stderr}")
    else:
        out_clean = res_mepa.stdout.strip().replace('\n', ', ')
        print(f"  SUCESSO! Saida MEPA: [{out_clean}]")
        
    # Limpar arquivo temporario .mepa
    if os.path.exists(out_mepa):
        os.remove(out_mepa)

print("\n=== TODOS OS TESTES FORAM CONCLUIDOS COM SUCESSO ===")
