"""
Gerador de Código: Fortran 77 para VM

Registos da VM:
gp: base de variáveis globais (programa principal)
fp: base de variáveis locais (funções/subroutines)
sp: topo da pilha

Convenções adoptadas:
- Variáveis do programa principal -> PUSHG/STOREG (gp-relativo)
- Variáveis locais de subprogramas -> PUSHL/STOREL (fp-relativo)
- Arrays -> bloco alocado em heap; o endereço fica na posição da variável
- Passagem de parâmetros -> por valor (simplificação)
- Valor de retorno de funções -> variável local com o nome da função (PUSHL n)
"""

from semantic import SymbolTable, Symbol, implicit_type


class CodeGenError(Exception):
    pass


class CodeGenerator:
    def __init__(self, sa):
        """
        sa — SemanticAnalyzer já executado com ast anotada.
        """
        self.sa          = sa
        self.code        : list[str] = []
        self.label_count : int = 0
        self.current_scope : SymbolTable = sa.global_table
        self.is_global   : bool = True
        # mapa label Fortran -> label VM
        self.fortran_labels : dict[int, str] = {}


    # ------------------------------------------------------------------
    # Utilitários de emissão
    # ------------------------------------------------------------------
    def emit(self, instr: str):
        self.code.append(instr)

    def new_label(self, prefix='L') -> str:
        self.label_count += 1
        return f'{prefix}{self.label_count}'

    def label_for(self, fortran_lbl: int) -> str:
        if fortran_lbl not in self.fortran_labels:
            self.fortran_labels[fortran_lbl] = self.new_label('FL')
        return self.fortran_labels[fortran_lbl]

    def get_code(self) -> str:
        return '\n'.join(self.code)

    # ------------------------------------------------------------------
    # Offsets de variáveis
    # ------------------------------------------------------------------
    def assign_offsets(self, scope: SymbolTable):
        """Atribui offset sequencial a cada símbolo na tabela."""
        offset = 0
        for sym in scope.symbols.values():
            sym.offset = offset
            offset += 1

    def assign_offsets_function(self, scope: SymbolTable, params: list[str]):
        """
        Convenção de chamada EWVM:
          - Parâmetros chegam na pilha ANTES do CALL.
            Após CALL, fp aponta ao topo; parâmetros ficam em posições negativas:
            param[0] -> fp[ -(n_params) ], ..., param[-1] -> fp[-1]
          - Variáveis locais (incluindo variável de retorno) -> fp[0], fp[1], ...
        """
        n = len(params)
        for i, pname in enumerate(params):
            sym = scope.lookup_local(pname)
            if sym:
                sym.offset = -(n - i)   # negativo

        # Variáveis locais (não-parâmetros) em ordem, a partir de 0
        local_offset = 0
        for sym in scope.symbols.values():
            if sym.offset is None or sym.offset >= 0:
                # ainda não tem offset (ou é a var de retorno da função)
                sym.offset = local_offset
                local_offset += 1

    def push_var(self, name: str):
        sym = self.current_scope.lookup(name)
        if sym is None:
            raise CodeGenError(f"Variável '{name}' não encontrada")
        if self.is_global:
            self.emit(f'PUSHG {sym.offset}')
        else:
            self.emit(f'PUSHL {sym.offset}')

    def store_var(self, name: str):
        sym = self.current_scope.lookup(name)
        if sym is None:
            raise CodeGenError(f"Variável '{name}' não encontrada")
        if self.is_global:
            self.emit(f'STOREG {sym.offset}')
        else:
            self.emit(f'STOREL {sym.offset}')

    # ------------------------------------------------------------------
    # Geração principal
    # ------------------------------------------------------------------
    def generate(self, ast):
        if ast is None:
            return ''
        units = ast.get('units', [])

        # Separar programa principal de subprogramas
        main_unit = None
        sub_units = []
        for u in units:
            if u['kind'] == 'main_program':
                main_unit = u
            else:
                sub_units.append(u)

        # Código principal
        if main_unit:
            self._gen_main(main_unit)

        # Subprogramas
        for u in sub_units:
            self.emit('')
            if u['kind'] == 'function':
                self._gen_function(u)
            elif u['kind'] == 'subroutine':
                self._gen_subroutine(u)

        return self.get_code()

    # ------------------------------------------------------------------
    def _gen_main(self, u):
        scope = u.get('symtable')
        if scope is None:
            scope = self.sa.global_table
        self.current_scope = scope
        self.is_global = True
        self.assign_offsets(scope)

        n_vars = len(scope.symbols)

        self.emit('START')
        if n_vars > 0:
            self.emit(f'PUSHN {n_vars}')

        self._alloc_arrays(scope)
        self._stmts(u['body'])
        self.emit('STOP')

    # ------------------------------------------------------------------
    def _gen_function(self, u):
        scope = u.get('symtable')
        if scope is None:
            return
        self.current_scope = scope
        self.is_global = False
        # Primeiro, zerar todos os offsets
        for sym in scope.symbols.values():
            sym.offset = None
        self.assign_offsets_function(scope, u['params'])

        fn_label = u['name'].upper()

        # Contar variáveis locais (offset >= 0)
        n_locals = sum(1 for sym in scope.symbols.values() if sym.offset >= 0)

        self.emit(f'{fn_label}:')
        if n_locals > 0:
            self.emit(f'PUSHN {n_locals}')

        self._alloc_arrays(scope)
        self._stmts(u['body'])

        # valor de retorno: variável local com o nome da função
        ret_sym = scope.lookup_local(u['name'])
        if ret_sym is not None:
            self.emit(f'PUSHL {ret_sym.offset}')
        else:
            self.emit('PUSHI 0')

        self.emit('RETURN')

    # ------------------------------------------------------------------
    def _gen_subroutine(self, u):
        scope = u.get('symtable')
        if scope is None:
            return
        self.current_scope = scope
        self.is_global = False
        for sym in scope.symbols.values():
            sym.offset = None
        self.assign_offsets_function(scope, u['params'])

        sr_label = u['name'].upper()
        n_locals = sum(1 for sym in scope.symbols.values() if sym.offset >= 0)

        self.emit(f'{sr_label}:')
        if n_locals > 0:
            self.emit(f'PUSHN {n_locals}')

        self._alloc_arrays(scope)
        self._stmts(u['body'])
        self.emit('RETURN')

    # ------------------------------------------------------------------
    def _alloc_arrays(self, scope: SymbolTable):
        for sym in scope.symbols.values():
            if sym.is_array and sym.array_size is not None:
                self.emit(f'ALLOC {sym.array_size}')
                if self.is_global:
                    self.emit(f'STOREG {sym.offset}')
                else:
                    self.emit(f'STOREL {sym.offset}')

    # ------------------------------------------------------------------
    def _stmts(self, stmts):
        for s in stmts:
            if s is not None:
                self._stmt(s)

    def _stmt(self, s):
        kind = s['kind']

        # Emitir label Fortran se existir (apenas em stmts que têm label próprio) (Diferente do label do GOTO)
        if kind != 'goto':
            lbl = s.get('label')
            if lbl is not None:
                vm_lbl = self.label_for(lbl)
                self.emit(f'{vm_lbl}:')

        if kind == 'declaration':
            pass  # já tratado na alocação

        elif kind == 'assign':
            if s['index'] is not None:
                # array[index] = value
                self.push_var(s['target'])          # endereço base do array
                self._expr(s['index'])              # índice (0-based -> -1)
                self.emit('PUSHI 1')
                self.emit('SUB')                    # offset = index - 1
                self.emit('PADD')                   # endereço final
                self._expr(s['value'])
                self.emit('STORE 0')
            else:
                self._expr(s['value'])
                self.store_var(s['target'])

        elif kind == 'print':
            for item in s['items']:
                self._expr(item)
                dtype = self._expr_type(item)
                if dtype == 'REAL':
                    self.emit('WRITEF')
                elif dtype == 'CHARACTER':
                    self.emit('WRITES')
                else:
                    self.emit('WRITEI')
            self.emit('WRITELN')

        elif kind == 'read':
            for item in s['items']:
                self.emit('READ')
                if isinstance(item, dict) and item.get('kind') == 'array_ref':
                    sym = self.current_scope.lookup(item['name'])
                    dtype = sym.dtype if sym else 'INTEGER'
                    if dtype == 'REAL':
                        self.emit('ATOF')
                    else:
                        self.emit('ATOI')
                    # armazenar no array
                    self.push_var(item['name'])
                    self._expr(item['index'])
                    self.emit('PUSHI 1')
                    self.emit('SUB')
                    self.emit('PADD')
                    self.emit('SWAP')
                    self.emit('STORE 0')
                else:
                    sym = self.current_scope.lookup(item) if isinstance(item, str) else None
                    dtype = sym.dtype if sym else 'INTEGER'
                    if dtype == 'REAL':
                        self.emit('ATOF')
                    else:
                        self.emit('ATOI')
                    name = item if isinstance(item, str) else item.get('name', item)
                    self.store_var(name)

        elif kind == 'if':
            else_lbl = self.new_label('ELSE')
            end_lbl  = self.new_label('ENDIF')
            self._expr(s['cond'])
            self.emit(f'JZ {else_lbl}')
            self._stmts(s['then_body'])
            if s['else_body']:
                self.emit(f'JUMP {end_lbl}')
                self.emit(f'{else_lbl}:')
                self._stmts(s['else_body'])
                self.emit(f'{end_lbl}:')
            else:
                self.emit(f'{else_lbl}:')

        elif kind == 'if_inline':
            end_lbl = self.new_label('ENDIF')
            self._expr(s['cond'])
            self.emit(f'JZ {end_lbl}')
            if s['stmt']:
                self._stmt(s['stmt'])
            self.emit(f'{end_lbl}:')

        elif kind == 'do':
            # DO end_label var = start, end [, step]
            var      = s['var']
            step     = s['step']
            loop_start = self.new_label('DO')
            loop_end   = self.new_label('DOEND')

            # Registar o label Fortran do CONTINUE a apontar para o incremento
            continue_lbl = self.label_for(s['end_label'])

            # inicializar variável de controlo
            self._expr(s['start'])
            self.store_var(var)

            self.emit(f'{loop_start}:')
            # condição: var <= end
            self.push_var(var)
            self._expr(s['end'])
            self.emit('INFEQ')
            self.emit(f'JZ {loop_end}')

            self._stmts(s['body'])

            # O label do CONTINUE aponta aqui (incremento)
            self.emit(f'{continue_lbl}:')
            # incremento
            self.push_var(var)
            if step:
                self._expr(step)
            else:
                self.emit('PUSHI 1')
            self.emit('ADD')
            self.store_var(var)
            self.emit(f'JUMP {loop_start}')
            self.emit(f'{loop_end}:')
            # O label Fortran do CONTINUE já foi emitido no body

        elif kind == 'goto':
            vm_lbl = self.label_for(s['label'])
            self.emit(f'JUMP {vm_lbl}')

        elif kind == 'continue':
            self.emit('NOP')

        elif kind == 'stop':
            self.emit('STOP')

        elif kind == 'return':
            # para funções: empilhar valor de retorno antes
            if self.current_function_name():
                sym = self.current_scope.lookup_local(self.current_function_name())
                if sym is not None:
                    self.emit(f'PUSHL {sym.offset}')
            self.emit('RETURN')

        elif kind == 'call':
            # empilhar argumentos
            for a in s['args']:
                self._expr(a)
            self.emit(f'PUSHA {s["name"].upper()}')
            self.emit('CALL')
            # descartar valor de retorno se houver (CALL não usa retorno)
            gsym = self.sa.global_table.lookup(s['name'])
            if gsym and gsym.ret_type and gsym.ret_type != 'VOID':
                self.emit('POP 1')

        elif kind == 'label_only':
            pass  # label já emitido acima

    # ------------------------------------------------------------------
    def _expr(self, e):
        if e is None:
            return
        kind = e['kind']

        if kind == 'INT_LIT':
            self.emit(f'PUSHI {e["value"]}')
        elif kind == 'FLOAT_LIT':
            self.emit(f'PUSHF {e["value"]}')
        elif kind == 'STR_LIT':
            self.emit(f'PUSHS "{e["value"]}"')
        elif kind == 'BOOL_LIT':
            self.emit(f'PUSHI {1 if e["value"] else 0}')

        elif kind == 'id':
            self.push_var(e['name'])

        elif kind == 'array_ref':
            self.push_var(e['name'])     #endereço base
            self._expr(e['index'])       #indice
            self.emit('PUSHI 1')
            self.emit('SUB')             #offset = index - 1
            self.emit('PADD')            #endereço final = base + offset
            self.emit('LOAD 0')          #carrega heap[addr]

        elif kind == 'binop':
            op = e['op']
            lt = self._expr_type(e['left'])
            rt = self._expr_type(e['right'])
            use_float = (lt == 'REAL' or rt == 'REAL')

            self._expr(e['left'])
            # conversão, se necessário
            if use_float and lt != 'REAL':
                self.emit('ITOF')
            self._expr(e['right'])
            if use_float and rt != 'REAL':
                self.emit('ITOF')

            ops = {
                '+': 'FADD' if use_float else 'ADD',
                '-': 'FSUB' if use_float else 'SUB',
                '*': 'FMUL' if use_float else 'MUL',
                '/': 'FDIV' if use_float else 'DIV',
                '**': 'ERR "power not natively supported"',
                '.EQ.': 'EQUAL',
                '.NE.': 'EQUAL\nNOT',
                '.LT.': 'FINF' if use_float else 'INF',
                '.LE.': 'FINFEQ' if use_float else 'INFEQ',
                '.GT.': 'FSUP' if use_float else 'SUP',
                '.GE.': 'FSUPEQ' if use_float else 'SUPEQ',
                '.AND.': 'AND',
                '.OR.': 'OR',
            }
            instr = ops.get(op)
            if instr:
                for line in instr.split('\n'):
                    self.emit(line)

        elif kind == 'unop':
            op = e['op']
            self._expr(e['operand'])
            if op == 'UMINUS':
                dtype = self._expr_type(e['operand'])
                if dtype == 'REAL':
                    self.emit('PUSHF -1.0')
                    self.emit('FMUL')
                else:
                    self.emit('PUSHI -1')
                    self.emit('MUL')
            elif op == 'NOT':
                self.emit('NOT')

        elif kind == 'func_call':
            for a in e['args']:
                self._expr(a)
            self.emit(f'PUSHA {e["name"].upper()}')
            self.emit('CALL')
            # resultado fica no topo da pilha

        elif kind == 'array_or_call':
            # não deveria chegar aqui após semântica
            self._expr({'kind': 'array_ref', 'name': e['name'],
                        'index': e.get('index_or_args')})

        elif kind == 'intrinsic':
            name = e['name']
            args = e['args']
            if name == 'MOD':
                self._expr(args[0])
                self._expr(args[1])
                self.emit('MOD')
            elif name in ('ABS', 'IABS'):
                self._expr(args[0])
                dtype = self._expr_type(args[0])
                lbl_pos = self.new_label('ABS')
                lbl_end = self.new_label('ABSEND')
                self.emit('DUP 1')
                self.emit('PUSHI 0')
                self.emit('INFEQ' if dtype != 'REAL' else 'FINFEQ')
                self.emit(f'JZ {lbl_pos}')
                if dtype == 'REAL':
                    self.emit('PUSHF -1.0')
                    self.emit('FMUL')
                else:
                    self.emit('PUSHI -1')
                    self.emit('MUL')
                self.emit(f'JUMP {lbl_end}')
                self.emit(f'{lbl_pos}:')
                self.emit(f'{lbl_end}:')
            elif name == 'SQRT':
                self._expr(args[0])
                dtype = self._expr_type(args[0])
                if dtype != 'REAL':
                    self.emit('ITOF')
                # VM não tem SQRT nativo; aproximação via ERR ou comentário
                self.emit('ERR "SQRT not natively supported by VM"')
            elif name == 'INT':
                self._expr(args[0])
                dtype = self._expr_type(args[0])
                if dtype == 'REAL':
                    self.emit('FTOI')
            elif name == 'FLOAT':
                self._expr(args[0])
                self.emit('ITOF')
            elif name in ('MAX', 'MIN'):
                # empilhar todos e comparar sequencialmente
                self._expr(args[0])
                for a in args[1:]:
                    self._expr(a)
                    self.emit('DUP 1')
                    self.emit(f'ERR "{name} with >2 args not supported"')

    # ------------------------------------------------------------------
    def _expr_type(self, e) -> str:
        """Determina o tipo de uma expressão sem emitir código."""
        if e is None:
            return 'INTEGER'
        kind = e['kind']
        if kind == 'INT_LIT' or kind == 'BOOL_LIT':
            return 'INTEGER'
        if kind == 'FLOAT_LIT':
            return 'REAL'
        if kind == 'STR_LIT':
            return 'CHARACTER'
        if kind == 'id':
            sym = self.current_scope.lookup(e['name'])
            return sym.dtype if sym else implicit_type(e['name'])
        if kind == 'array_ref':
            sym = self.current_scope.lookup(e['name'])
            return sym.dtype if sym else 'INTEGER'
        if kind == 'binop':
            op = e['op']
            if op in ('.EQ.', '.NE.', '.LT.', '.LE.', '.GT.', '.GE.',
                      '.AND.', '.OR.'):
                return 'LOGICAL'
            lt = self._expr_type(e['left'])
            rt = self._expr_type(e['right'])
            return 'REAL' if (lt == 'REAL' or rt == 'REAL') else 'INTEGER'
        if kind == 'unop':
            return self._expr_type(e['operand'])
        if kind == 'func_call':
            sym = self.sa.global_table.lookup(e['name'])
            return sym.ret_type if sym else implicit_type(e['name'])
        if kind == 'intrinsic':
            name = e['name']
            if name in ('MOD', 'IABS', 'INT'):
                return 'INTEGER'
            if name in ('ABS', 'SQRT', 'FLOAT'):
                return 'REAL'
            return 'INTEGER'
        return 'INTEGER'

    def current_function_name(self) -> str | None:
        if not self.is_global:
            return self.current_scope.name
        return None


def generate(ast, sa) -> str:
    gen = CodeGenerator(sa)
    return gen.generate(ast)
