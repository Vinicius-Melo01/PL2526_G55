"""
Fortran 77 Parser: ply.yacc
Constrói uma AST (lista de nós como tuplos/dicionários).
"""

import ply.yacc as yacc
from lexer import tokens, build_lexer, preprocess_fixed_form

# Precedência de operadores
precedence = (
    ('left',  'OR'),
    ('left',  'AND'),
    ('right', 'NOT'),
    ('left',  'EQ', 'NE', 'LT', 'LE', 'GT', 'GE'),
    ('left',  'PLUS', 'MINUS'),
    ('left',  'STAR', 'DIVIDE'),
    ('right', 'UMINUS'),
    ('right', 'POWER'),
)

# Nó auxiliar
def node(kind, **kwargs):
    return {'kind': kind, **kwargs}


# Gramática:

# Programa completo
def p_program(p):
    '''program : program_unit_list'''
    p[0] = node('program', units=p[1])

def p_program_unit_list_multi(p):
    '''program_unit_list : program_unit_list program_unit'''
    p[0] = p[1] + [p[2]]

def p_program_unit_list_single(p):
    '''program_unit_list : program_unit'''
    p[0] = [p[1]]

def p_program_unit(p):
    '''program_unit : main_program
                    | function_subprogram
                    | subroutine_subprogram'''
    p[0] = p[1]

# --- Programa principal ---
def p_main_program(p):
    '''main_program : PROGRAM ID NEWLINE statement_list END NEWLINE
                    | PROGRAM ID NEWLINE statement_list END'''
    p[0] = node('main_program', name=p[2], body=p[4])

# --- Subprograma FUNCTION ---
def p_function_subprogram(p):
    '''function_subprogram : type_spec FUNCTION ID LPAREN param_list RPAREN NEWLINE statement_list END NEWLINE
                           | type_spec FUNCTION ID LPAREN param_list RPAREN NEWLINE statement_list END
                           | FUNCTION ID LPAREN param_list RPAREN NEWLINE statement_list END NEWLINE
                           | FUNCTION ID LPAREN param_list RPAREN NEWLINE statement_list END'''
    if p[1] in ('INTEGER','REAL','LOGICAL','CHARACTER'):
        p[0] = node('function', ret_type=p[1], name=p[3], params=p[5], body=p[8])
    else:
        p[0] = node('function', ret_type=None, name=p[2], params=p[4], body=p[7])

# --- Subprograma SUBROUTINE ---
def p_subroutine_subprogram(p):
    '''subroutine_subprogram : SUBROUTINE ID LPAREN param_list RPAREN NEWLINE statement_list END NEWLINE
                             | SUBROUTINE ID LPAREN param_list RPAREN NEWLINE statement_list END
                             | SUBROUTINE ID LPAREN RPAREN NEWLINE statement_list END NEWLINE
                             | SUBROUTINE ID LPAREN RPAREN NEWLINE statement_list END'''
    if p[4] == ')':
        p[0] = node('subroutine', name=p[2], params=[], body=p[6])
    else:
        p[0] = node('subroutine', name=p[2], params=p[4], body=p[7])

def p_param_list_multi(p):
    '''param_list : param_list COMMA ID'''
    p[0] = p[1] + [p[3]]

def p_param_list_single(p):
    '''param_list : ID'''
    p[0] = [p[1]]

def p_param_list_empty(p):
    '''param_list : '''
    p[0] = []

# --- Lista de statements ---
def p_statement_list_multi(p):
    '''statement_list : statement_list statement'''
    if p[2] is not None:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = p[1]

def p_statement_list_single(p):
    '''statement_list : statement'''
    p[0] = [p[1]] if p[1] is not None else []

def p_statement(p):
    '''statement : labeled_statement
                 | unlabeled_statement'''
    p[0] = p[1]

def p_labeled_statement(p):
    '''labeled_statement : LABEL unlabeled_statement'''
    if p[2] is not None:
        p[2]['label'] = p[1]
        p[0] = p[2]
    else:
        p[0] = node('label_only', label=p[1])

def p_unlabeled_statement(p):
    '''unlabeled_statement : declaration_stmt
                           | assignment_stmt
                           | print_stmt
                           | read_stmt
                           | if_stmt
                           | do_stmt
                           | goto_stmt
                           | continue_stmt
                           | stop_stmt
                           | return_stmt
                           | call_stmt
                           | newline_stmt'''
    p[0] = p[1]

def p_newline_stmt(p):
    '''newline_stmt : NEWLINE'''
    p[0] = None

# --- Declarações de tipo ---
def p_declaration_stmt(p):
    '''declaration_stmt : type_spec var_decl_list NEWLINE'''
    p[0] = node('declaration', dtype=p[1], vars=p[2])

def p_type_spec(p):
    '''type_spec : INTEGER
                 | REAL
                 | LOGICAL
                 | CHARACTER'''
    p[0] = p[1]

def p_var_decl_list_multi(p):
    '''var_decl_list : var_decl_list COMMA var_decl'''
    p[0] = p[1] + [p[3]]

def p_var_decl_list_single(p):
    '''var_decl_list : var_decl'''
    p[0] = [p[1]]

def p_var_decl_array(p):
    '''var_decl : ID LPAREN expr RPAREN'''
    p[0] = node('var', name=p[1], array_size=p[3])

def p_var_decl_scalar(p):
    '''var_decl : ID'''
    p[0] = node('var', name=p[1], array_size=None)

# --- Atribuição ---
def p_assignment_stmt(p):
    '''assignment_stmt : ID EQUALS expr NEWLINE
                       | ID LPAREN expr RPAREN EQUALS expr NEWLINE'''
    if len(p) == 5:
        p[0] = node('assign', target=p[1], index=None, value=p[3])
    else:
        p[0] = node('assign', target=p[1], index=p[3], value=p[6])

# --- PRINTs ---
def p_print_stmt_star(p):
    '''print_stmt : PRINT STAR COMMA print_items NEWLINE'''
    p[0] = node('print', fmt='*', items=p[4])

def p_print_items_multi(p):
    '''print_items : print_items COMMA expr'''
    p[0] = p[1] + [p[3]]

def p_print_items_single(p):
    '''print_items : expr'''
    p[0] = [p[1]]

# --- READ ---
def p_read_stmt_star(p):
    '''read_stmt : READ STAR COMMA read_items NEWLINE'''
    p[0] = node('read', fmt='*', items=p[4])

def p_read_items_multi(p):
    '''read_items : read_items COMMA ID'''
    p[0] = p[1] + [p[3]]

def p_read_items_single(p):
    '''read_items : ID'''
    p[0] = [p[1]]

def p_read_items_array(p):
    '''read_items : ID LPAREN expr RPAREN'''
    p[0] = [node('array_ref', name=p[1], index=p[3])]

# --- IF ---
def p_if_stmt_block(p):
    '''if_stmt : IF LPAREN expr RPAREN THEN NEWLINE statement_list ENDIF NEWLINE
               | IF LPAREN expr RPAREN THEN NEWLINE statement_list ELSE NEWLINE statement_list ENDIF NEWLINE'''
    if len(p) == 10:
        p[0] = node('if', cond=p[3], then_body=p[7], else_body=[])
    else:
        p[0] = node('if', cond=p[3], then_body=p[7], else_body=p[10])

def p_if_stmt_arithmetic(p):
    '''if_stmt : IF LPAREN expr RPAREN unlabeled_statement'''
    p[0] = node('if_inline', cond=p[3], stmt=p[5])

# --- DO ---
def p_do_stmt(p):
    '''do_stmt : DO INT_LIT ID EQUALS expr COMMA expr NEWLINE statement_list LABEL CONTINUE NEWLINE'''
    p[0] = node('do', end_label=p[2], var=p[3], start=p[5], end=p[7], step=None, body=p[9])

def p_do_stmt_step(p):
    '''do_stmt : DO INT_LIT ID EQUALS expr COMMA expr COMMA expr NEWLINE statement_list LABEL CONTINUE NEWLINE'''
    p[0] = node('do', end_label=p[2], var=p[3], start=p[5], end=p[7], step=p[9], body=p[11])

# --- GOTO ---
def p_goto_stmt(p):
    '''goto_stmt : GOTO INT_LIT NEWLINE'''
    p[0] = node('goto', label=p[2])

# --- CONTINUE ---
def p_continue_stmt(p):
    '''continue_stmt : CONTINUE NEWLINE'''
    p[0] = node('continue')

# --- STOP ---
def p_stop_stmt(p):
    '''stop_stmt : STOP NEWLINE'''
    p[0] = node('stop')

# --- RETURN ---
def p_return_stmt(p):
    '''return_stmt : RETURN NEWLINE'''
    p[0] = node('return')

# --- CALL ---
def p_call_stmt(p):
    '''call_stmt : CALL ID LPAREN arg_list RPAREN NEWLINE
                 | CALL ID LPAREN RPAREN NEWLINE'''
    if len(p) == 7:
        p[0] = node('call', name=p[2], args=p[4])
    else:
        p[0] = node('call', name=p[2], args=[])


# Expressões:

def p_expr_binop(p):
    '''expr : expr PLUS expr
            | expr MINUS expr
            | expr STAR expr
            | expr DIVIDE expr
            | expr POWER expr
            | expr EQ expr
            | expr NE expr
            | expr LT expr
            | expr LE expr
            | expr GT expr
            | expr GE expr
            | expr AND expr
            | expr OR expr'''
    p[0] = node('binop', op=p[2], left=p[1], right=p[3])

def p_expr_unary_not(p):
    '''expr : NOT expr'''
    p[0] = node('unop', op='NOT', operand=p[2])

def p_expr_unary_minus(p):
    '''expr : MINUS expr %prec UMINUS'''
    p[0] = node('unop', op='UMINUS', operand=p[2])

def p_expr_paren(p):
    '''expr : LPAREN expr RPAREN'''
    p[0] = p[2]

def p_expr_INT_LIT(p):
    '''expr : INT_LIT'''
    p[0] = node('INT_LIT', value=p[1])

def p_expr_FLOAT_LIT(p):
    '''expr : FLOAT_LIT'''
    p[0] = node('FLOAT_LIT', value=p[1])

def p_expr_STR_LIT(p):
    '''expr : STR_LIT'''
    p[0] = node('STR_LIT', value=p[1])

def p_expr_BOOL_LIT(p):
    '''expr : BOOL_LIT'''
    p[0] = node('BOOL_LIT', value=p[1])

def p_expr_array_ref(p):
    '''expr : ID LPAREN expr RPAREN'''
    # pode ser chamada de função ou acesso a array (resolvido na semântica)
    p[0] = node('array_or_call', name=p[1], index_or_args=p[3])

def p_expr_func_call_multi(p):
    '''expr : ID LPAREN arg_list RPAREN'''
    p[0] = node('func_call', name=p[1], args=p[3])

def p_expr_id(p):
    '''expr : ID'''
    p[0] = node('id', name=p[1])

def p_expr_intrinsic_mod(p):
    '''expr : MOD LPAREN expr COMMA expr RPAREN'''
    p[0] = node('intrinsic', name='MOD', args=[p[3], p[5]])

def p_expr_intrinsic_abs(p):
    '''expr : ABS LPAREN expr RPAREN
            | IABS LPAREN expr RPAREN'''
    p[0] = node('intrinsic', name='ABS', args=[p[3]])

def p_expr_intrinsic_sqrt(p):
    '''expr : SQRT LPAREN expr RPAREN'''
    p[0] = node('intrinsic', name='SQRT', args=[p[3]])

def p_expr_intrinsic_int(p):
    '''expr : INT LPAREN expr RPAREN'''
    p[0] = node('intrinsic', name='INT', args=[p[3]])

def p_expr_intrinsic_float(p):
    '''expr : FLOAT LPAREN expr RPAREN'''
    p[0] = node('intrinsic', name='FLOAT', args=[p[3]])

def p_expr_intrinsic_max(p):
    '''expr : MAX LPAREN arg_list RPAREN'''
    p[0] = node('intrinsic', name='MAX', args=p[3])

def p_expr_intrinsic_min(p):
    '''expr : MIN LPAREN arg_list RPAREN'''
    p[0] = node('intrinsic', name='MIN', args=p[3])

def p_arg_list_multi(p):
    '''arg_list : arg_list COMMA expr'''
    p[0] = p[1] + [p[3]]

def p_arg_list_single(p):
    '''arg_list : expr'''
    p[0] = [p[1]]

# Erro
def p_error(p):
    if p:
        print(f"[Parser] Erro sintático: token '{p.type}' ('{p.value}') na linha {p.lineno}")
    else:
        print("[Parser] Erro sintático: fim de ficheiro inesperado")


# Interface pública

def build_parser(debug=False):
    lexer = build_lexer()
    parser = yacc.yacc(debug=debug, outputdir='/tmp')
    return parser, lexer

def parse(source: str, fixed_form: bool = True, debug: bool = False):
    if fixed_form:
        source = preprocess_fixed_form(source)
    parser, lexer = build_parser(debug=debug)
    ast = parser.parse(source, lexer=lexer, tracking=True)
    return ast


if __name__ == '__main__':
    import sys, pprint
    src = open(sys.argv[1]).read() if len(sys.argv) > 1 else """\
      PROGRAM HELLO
      PRINT *, 'Ola, Mundo!'
      END
"""
    ast = parse(src)
    pprint.pprint(ast)
