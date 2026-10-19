#!/usr/bin/env python3
"""
Interpretador MEPA 5.0 (Maquina de Execucao de Programas Abstratos)
Compativel com as especificacoes do laboratorio de compiladores (ECOI2219).
"""

import sys
import argparse

class MEPA:
    def __init__(self, silent=False):
        self.M = []          # Memoria de dados (pilha)
        self.s = -1          # Apontador do topo da pilha
        self.i = 0           # Contador de instrucoes (PC)
        self.instructions = []
        self.labels = {}
        self.silent = silent

    def load_program(self, code_lines):
        raw_instructions = []
        
        # Primeira passagem: limpar comentarios e identificar instrucoes/rotulos
        for line_num, line in enumerate(code_lines):
            line = line.strip()
            if not line or line.startswith(';'):
                continue
            # Remover comentario inline (; ...)
            if ';' in line:
                line = line[:line.index(';')].strip()
            if not line:
                continue

            # Pode haver rotulos: L1: CRVL 0,0 ou apenas L1:
            while ':' in line:
                colon_idx = line.index(':')
                prefix = line[:colon_idx].strip()
                # Verifica se eh um rotulo valido (ex: L1, L10)
                if ' ' not in prefix:
                    self.labels[prefix] = len(raw_instructions)
                    line = line[colon_idx+1:].strip()
                else:
                    break

            if line:
                raw_instructions.append(line)

        # Se houver rotulo no final do arquivo sem instrucao apos ele
        for lbl in list(self.labels.keys()):
            if self.labels[lbl] >= len(raw_instructions):
                self.labels[lbl] = len(raw_instructions)
        # Adicionar uma instrucao NADA ou PARA no fim se necessario
        raw_instructions.append("PARA")

        self.instructions = raw_instructions

    def run(self):
        self.i = 0
        self.s = -1
        self.M = []

        total = len(self.instructions)
        while self.i < total:
            instr_str = self.instructions[self.i]
            parts = instr_str.split(None, 1)
            op = parts[0].upper()
            args = parts[1].strip() if len(parts) > 1 else ""

            self.i += 1

            if op == "INPP":
                self.s = -1
                self.M = []
            elif op == "AMEM":
                k = int(args)
                self.M.extend([0] * k)
                self.s += k
            elif op == "DMEM":
                k = int(args)
                for _ in range(k):
                    if self.M:
                        self.M.pop()
                self.s -= k
            elif op == "CRCT":
                val = float(args) if '.' in args else int(args)
                self.M.append(val)
                self.s += 1
            elif op == "CRVL":
                # Formato: 0,offset
                offset = int(args.split(',')[1].strip())
                self.M.append(self.M[offset])
                self.s += 1
            elif op == "ARMZ":
                offset = int(args.split(',')[1].strip())
                val = self.M.pop()
                self.s -= 1
                if offset < len(self.M):
                    self.M[offset] = val
                else:
                    while len(self.M) <= offset:
                        self.M.append(0)
                    self.M[offset] = val
            elif op == "SOMA":
                b = self.M.pop()
                a = self.M.pop()
                self.M.append(a + b)
                self.s -= 1
            elif op == "SUBT" or op == "SUBTR":
                b = self.M.pop()
                a = self.M.pop()
                self.M.append(a - b)
                self.s -= 1
            elif op == "MULT":
                b = self.M.pop()
                a = self.M.pop()
                self.M.append(a * b)
                self.s -= 1
            elif op == "DIVI":
                b = self.M.pop()
                a = self.M.pop()
                self.M.append(a // b if isinstance(a, int) and isinstance(b, int) else a / b)
                self.s -= 1
            elif op == "INVR" or op == "INVE":
                self.M[-1] = -self.M[-1]
            elif op == "CONJ":
                b = self.M.pop()
                a = self.M.pop()
                self.M.append(1 if (a != 0 and b != 0) else 0)
                self.s -= 1
            elif op == "DISJ":
                b = self.M.pop()
                a = self.M.pop()
                self.M.append(1 if (a != 0 or b != 0) else 0)
                self.s -= 1
            elif op == "NEGA":
                a = self.M.pop()
                self.M.append(1 if a == 0 else 0)
            elif op == "CMIG":
                b = self.M.pop()
                a = self.M.pop()
                self.M.append(1 if a == b else 0)
                self.s -= 1
            elif op == "CMDG":
                b = self.M.pop()
                a = self.M.pop()
                self.M.append(1 if a != b else 0)
                self.s -= 1
            elif op == "CMME" or op == "CMMEN":
                b = self.M.pop()
                a = self.M.pop()
                self.M.append(1 if a < b else 0)
                self.s -= 1
            elif op == "CMEG":
                b = self.M.pop()
                a = self.M.pop()
                self.M.append(1 if a <= b else 0)
                self.s -= 1
            elif op == "CMMA" or op == "CMMAI":
                b = self.M.pop()
                a = self.M.pop()
                self.M.append(1 if a > b else 0)
                self.s -= 1
            elif op == "CMAG":
                b = self.M.pop()
                a = self.M.pop()
                self.M.append(1 if a >= b else 0)
                self.s -= 1
            elif op == "DSVS":
                target = args.strip()
                if target in self.labels:
                    self.i = self.labels[target]
                else:
                    raise RuntimeError(f"Rotulo indefinido: {target}")
            elif op == "DSVF":
                target = args.strip()
                cond = self.M.pop()
                self.s -= 1
                if cond == 0:
                    if target in self.labels:
                        self.i = self.labels[target]
                    else:
                        raise RuntimeError(f"Rotulo indefinido: {target}")
            elif op == "DSVT":
                target = args.strip()
                cond = self.M.pop()
                self.s -= 1
                if cond != 0:
                    if target in self.labels:
                        self.i = self.labels[target]
                    else:
                        raise RuntimeError(f"Rotulo indefinido: {target}")
            elif op == "IMPR":
                val = self.M.pop()
                self.s -= 1
                print(val)
            elif op == "LEIT":
                val_str = input()
                val = int(val_str)
                self.M.append(val)
                self.s += 1
            elif op == "PARA" or op == "FIM":
                break
            elif op == "NADA":
                pass
            else:
                pass

def main():
    parser = argparse.ArgumentParser(description="Interpretador MEPA 5.0")
    parser.add_argument("--progfile", required=True, help="Arquivo com instrucoes MEPA")
    parser.add_argument("--silent", action="store_true", help="Modo silencioso")
    args = parser.parse_args()

    try:
        with open(args.progfile, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(args.progfile, 'r', encoding='utf-16') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(args.progfile, 'r', encoding='latin-1') as f:
                lines = f.readlines()

    vm = MEPA(silent=args.silent)
    vm.load_program(lines)
    vm.run()

if __name__ == '__main__':
    main()
