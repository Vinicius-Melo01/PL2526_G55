#!/bin/bash
# Gera todos os ficheiros VM na pasta output/

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/output"

# Criar pasta output se não existir
mkdir -p "$OUTPUT_DIR"

# Apagar ficheiros .vm existentes
echo "A limpar output/*.vm ..."
rm -f "$OUTPUT_DIR"/*.vm

# Compilar cada teste
echo "A compilar testes..."

python3 "$SCRIPT_DIR/compiler.py" "$SCRIPT_DIR/tests/hello.f77"     -o "$OUTPUT_DIR/hello.vm"     && echo "[OK] hello.vm"
python3 "$SCRIPT_DIR/compiler.py" "$SCRIPT_DIR/tests/fatorial.f77"  -o "$OUTPUT_DIR/fatorial.vm"  && echo "[OK] fatorial.vm"
python3 "$SCRIPT_DIR/compiler.py" "$SCRIPT_DIR/tests/primo.f77"     -o "$OUTPUT_DIR/primo.vm"     && echo "[OK] primo.vm"
python3 "$SCRIPT_DIR/compiler.py" "$SCRIPT_DIR/tests/somaarr.f77"   -o "$OUTPUT_DIR/somaarr.vm"   && echo "[OK] somaarr.vm"
python3 "$SCRIPT_DIR/compiler.py" "$SCRIPT_DIR/tests/conversor.f77" -o "$OUTPUT_DIR/conversor.vm" && echo "[OK] conversor.vm"

echo ""
echo "Ficheiros gerados em $OUTPUT_DIR:"
ls -1 "$OUTPUT_DIR"/*.vm 2>/dev/null || echo "(nenhum ficheiro gerado)"
