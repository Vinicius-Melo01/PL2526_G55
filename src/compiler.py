"""
fortran77c — Compilador Fortran 77 → VM
Uso:
  python compiler.py <ficheiro.f77> [-o saida.vm] [--ast] [--tokens] [--free]
"""

import sys
import argparse
import os
sys.path.insert(0, os.path.dirname(__file__))

from lexer   import tokenize, preprocess_fixed_form
from parser  import parse
from semantic import analyze
from codegen import generate


def compile_source(source: str, fixed_form: bool = True,
                   show_tokens: bool = False,
                   show_ast: bool = False) -> str:
    # --- Léxico ---
    if show_tokens:
        print("=== TOKENS ===")
        toks, erros = tokenize(source, fixed_form=fixed_form)
        for tok in toks:
            print(tok)
        if erros:
            for e in erros: print(e)
        print()

    # --- Sintático ---
    ast = parse(source, fixed_form=fixed_form)
    if ast is None:
        print("[Erro] Parse falhou — sem AST.", file=sys.stderr)
        return ""

    if show_ast:
        import pprint
        print("=== AST ===")
        pprint.pprint(ast)
        print()

    # --- Semântica ---
    sa = analyze(ast)
    if sa.errors:
        print(f"[Aviso] {len(sa.errors)} erro(s) semântico(s) detectados.", file=sys.stderr)

    # --- Geração de código ---
    vm_code = generate(ast, sa)
    return vm_code


def main():
    ap = argparse.ArgumentParser(description='Compilador Fortran 77 → VM')
    ap.add_argument('input', help='Ficheiro Fortran 77 (.f77 / .f)')
    ap.add_argument('-o', '--output', default=None, help='Ficheiro de saída VM')
    ap.add_argument('--tokens', action='store_true', help='Mostrar tokens')
    ap.add_argument('--ast',    action='store_true', help='Mostrar AST')
    ap.add_argument('--free',   action='store_true', help='Formato livre (não fixo)')
    args = ap.parse_args()

    try:
        with open(args.input, 'r') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"[Erro] Ficheiro '{args.input}' não encontrado.", file=sys.stderr)
        sys.exit(1)

    vm_code = compile_source(
        source,
        fixed_form=not args.free,
        show_tokens=args.tokens,
        show_ast=args.ast,
    )

    if not vm_code:
        sys.exit(1)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(vm_code)
        print(f"[OK] Código VM escrito em '{args.output}'")
    else:
        print(vm_code)


if __name__ == '__main__':
    main()
