"""
Fortran 77 Lexer — ply.lex
"""

import ply.lex as lex
import re

# Palavras-chave
reserved = {
    'PROGRAM'    : 'PROGRAM',
    'END'        : 'END',
    'INTEGER'    : 'INTEGER',
    'REAL'       : 'REAL',
    'LOGICAL'    : 'LOGICAL',
    'CHARACTER'  : 'CHARACTER',
    'IF'         : 'IF',
    'THEN'       : 'THEN',
    'ELSE'       : 'ELSE',
    'ENDIF'      : 'ENDIF',
    'DO'         : 'DO',
    'CONTINUE'   : 'CONTINUE',
    'GOTO'       : 'GOTO',
    'READ'       : 'READ',
    'PRINT'      : 'PRINT',
    'STOP'       : 'STOP',
    'RETURN'     : 'RETURN',
    'CALL'       : 'CALL',
    'SUBROUTINE' : 'SUBROUTINE',
    'FUNCTION'   : 'FUNCTION',
    'COMMON'     : 'COMMON',
    'DIMENSION'  : 'DIMENSION',
    'DATA'       : 'DATA',
    'PARAMETER'  : 'PARAMETER',
    'WRITE'      : 'WRITE',
    'FORMAT'     : 'FORMAT',
    'IMPLICIT'   : 'IMPLICIT',
    'NONE'       : 'NONE',
    'MOD'        : 'MOD',
    'ABS'        : 'ABS',
    'SQRT'       : 'SQRT',
    'INT'        : 'INT',
    'FLOAT'      : 'FLOAT',
    'DBLE'       : 'DBLE',
    'MAX'        : 'MAX',
    'MIN'        : 'MIN',
    'IABS'       : 'IABS',
}


# Lista de todos os tokens (vocabulario): Concatenação entre a lista de palavras reservadas com os novos tokens
tokens = list(reserved.values()) + [
    # Literais
    'INT_LIT',          
    'FLOAT_LIT',    
    'STR_LIT',    
    'BOOL_LIT',    
    # Identificadores
    'ID',
    # Label
    'LABEL',
    # Operadores relacionais
    'EQ', 'NE', 'LT', 'LE', 'GT', 'GE',
    # Operadores lógicos
    'AND', 'OR', 'NOT',
    # Operadores aritméticos
    'PLUS', 'MINUS', 'DIVIDE', 'POWER',
    # Pontuação
    'LPAREN', 'RPAREN', 'COMMA', 'EQUALS', 'COLON',
    'STAR',
    'NEWLINE',
]

# Pré-processamento de formato fixo

# Converte fonte Fortran 77 em formato fixo para linhas limpas, preservando a informação de label.
# Devolve texto onde cada linha de código começa com: LABEL<espaços>CÓDIGO
def preprocess_fixed_form(source: str) -> str:
    lines = source.splitlines()
    result = []
    current_stmt = None

    for raw in lines:
        # Normalizar para 72 colunas (ou menos)
        line = raw[:72]
        if not line.strip():
            continue

        col1 = line[0] if len(line) > 0 else ' '

        # Linha de comentário
        if col1 in ('C', 'c', '*', '!'):
            continue

        # Linha de continuação
        col6 = line[5] if len(line) > 5 else ' '
        if col6 not in (' ', '0', ''):
            if current_stmt is not None:
                current_stmt += ' ' + line[6:].strip()
            continue

        # Nova instrução
        if current_stmt is not None:
            result.append(current_stmt)

        label_part = line[:5].strip()
        code_part  = line[6:].strip() if len(line) > 6 else ''

        if label_part:
            current_stmt = f'#{label_part}# {code_part}'
        else:
            current_stmt = code_part

    if current_stmt is not None:
        result.append(current_stmt)

    return '\n'.join(result) + '\n'


# Regras do lexer

# Estado simples
t_PLUS   = r'\+'
t_MINUS  = r'-'
t_DIVIDE = r'/'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_COMMA  = r','
t_EQUALS = r'='
t_COLON  = r':'

#  NOTA: ** deve ser ANTES de *
def t_POWER(t):
    r'\*\*'
    return t

def t_STAR(t):
    r'\*'
    return t

def t_CONCAT(t):
    r'//'
    return t

# Operadores relacionais do Fortran
def t_EQ(t):
    r'\.EQ\.|\.eq\.'
    return t

def t_NE(t):
    r'\.NE\.|\.ne\.'
    return t

def t_LE(t):
    r'\.LE\.|\.le\.'
    return t

def t_LT(t):
    r'\.LT\.|\.lt\.'
    return t

def t_GE(t):
    r'\.GE\.|\.ge\.'
    return t

def t_GT(t):
    r'\.GT\.|\.gt\.'
    return t

def t_AND(t):
    r'\.AND\.|\.and\.'
    return t

def t_OR(t):
    r'\.OR\.|\.or\.'
    return t

def t_NOT(t):
    r'\.NOT\.|\.not\.'
    return t

def t_BOOL_LIT(t):
    r'\.TRUE\.|\.FALSE\.|\.true\.|\.false\.'
    t.value = t.value.upper() == '.TRUE.'
    return t

def t_LABEL(t):
    r'\#\d+\#'
    t.value = int(t.value[1:-1])
    return t

def t_FLOAT_LIT(t):
    r'\d+\.\d*([EeDd][+-]?\d+)?|\d+[EeDd][+-]?\d+'
    t.value = float(t.value.replace('D', 'E').replace('d', 'e'))
    return t

def t_INT_LIT(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_STR_LIT(t):
    r"'([^']|'')*'"
    t.value = t.value[1:-1].replace("''", "'")
    return t

def t_ID(t):
    r'[A-Za-z][A-Za-z0-9_]*'
    t.type = reserved.get(t.value.upper(), 'ID')
    t.value = t.value.upper()
    return t

def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    return t

t_ignore = ' \t\r'

def t_error(t):
    print(f"[Lexer] Caracter ilegal '{t.value[0]}' na linha {t.lexer.lineno}")
    t.lexer.skip(1)



def build_lexer(debug=False):
    return lex.lex(debug=debug, optimize=False)

# Devolve lista de tokens a partir do código fonte
def tokenize(source: str, fixed_form: bool = True, debug: bool = False):
    if fixed_form:
        source = preprocess_fixed_form(source)
    lexer = build_lexer(debug=debug) # Cria Lexer novo
    lexer.input(source)
    toks = []
    while True:
        tok = lexer.token()
        if tok is None:
            break
        toks.append(tok)
    return toks


if __name__ == '__main__':
    import sys
    src = open(sys.argv[1]).read() if len(sys.argv) > 1 else """\
      PROGRAM HELLO
      PRINT *, 'Ola, Mundo!'
      END
    """
    for tok in tokenize(src):
        print(tok)
