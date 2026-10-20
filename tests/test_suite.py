import os
import subprocess
import sys

# Diretorio base do projeto (um nivel acima de tests/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES_DIR = os.path.join(BASE_DIR, "examples") if os.path.isdir(os.path.join(BASE_DIR, "examples")) else os.path.join(BASE_DIR, "exemplos")

EXAMPLES = [
    (os.path.join(EXAMPLES_DIR, "expr.uc"), None),
    (os.path.join(EXAMPLES_DIR, "decl.uc"), None),
    (os.path.join(EXAMPLES_DIR, "precedencia.uc"), None),
    (os.path.join(EXAMPLES_DIR, "if.uc"), None),
    (os.path.join(EXAMPLES_DIR, "while.uc"), None),
    (os.path.join(EXAMPLES_DIR, "break.uc"), None),
    (os.path.join(EXAMPLES_DIR, "dowhile.uc"), None),
    (os.path.join(EXAMPLES_DIR, "fib.uc"), "10\n"),
]

python_exe = sys.executable
compiler_script = os.path.join(BASE_DIR, "src", "lab1_tds.py")
mepa_script = os.path.join(BASE_DIR, "mepa", "mepa_pt.py")

MVP_OUTPUT_DIR = os.path.join(BASE_DIR, "mvpOutput")
os.makedirs(MVP_OUTPUT_DIR, exist_ok=True)

print(" EXECUTANDO BATERIA DE TESTES DO COMPILADOR ")
for uc_file, input_data in EXAMPLES:
    base_name = os.path.splitext(os.path.basename(uc_file))[0]
    out_mepa = os.path.join(EXAMPLES_DIR, f"{base_name}.mepa")
    rel_path = os.path.relpath(uc_file, BASE_DIR)
    print(f"\n[TESTE] Compilando {rel_path}...")

    # Compilar
    res_comp = subprocess.run([python_exe, compiler_script, uc_file], capture_output=True, text=True)
    if res_comp.returncode != 0:
        print(f"  FALHA NA COMPILACAO:\n{res_comp.stderr}")
        continue

    with open(out_mepa, "w", encoding="utf-8") as f:
        f.write(res_comp.stdout)
    print(f"  Compilado com sucesso ({len(res_comp.stdout.splitlines())} instrucoes emitidas).")

    # Salvar codigo MEPA gerado em mvpOutput/<nome>.txt
    out_mvp = os.path.join(MVP_OUTPUT_DIR, f"{base_name}.txt")
    with open(out_mvp, "w", encoding="utf-8") as f:
        f.write(res_comp.stdout)
    print(f"  Codigo MEPA salvo em mvpOutput/{base_name}.txt")

    # Executar no MEPA
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

print("\n TODOS OS TESTES FORAM CONCLUIDOS COM SUCESSO ")
