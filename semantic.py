"""
Análise Semântica:
-Tabela de símbolos por âmbito (global / função / subroutine)
-Inferência de tipo 
-Verificação de tipos básica
-Resolução de array_or_call
"""

class SemanticError(Exception):
    pass


class Symbol:
    """
    Classe que representa uma entrada na tabela de símbolos
    """
    def __init__(self, name, dtype, is_array=False, array_size=None,
                 is_param=False, is_function=False, params=None, ret_type=None):
        self.name       = name
        self.dtype      = dtype          # 'INTEGER', 'REAL', 'LOGICAL', 'CHARACTER'
        self.is_array   = is_array
        self.array_size = array_size
        self.is_param   = is_param
        self.is_function = is_function
        self.params     = params or []
        self.ret_type   = ret_type
        self.offset     = None 


class SymbolTable:
    """ 
    Classe que representa a tabela de símbolos, com suporte a âmbitos aninhados.
    Cada âmbito tem um ponteiro para o pai, permitindo lookup hierárquico
    """
    def __init__(self, name='global', parent=None):
        self.name    = name
        self.parent  = parent
        self.symbols : dict[str, Symbol] = {}

    def declare(self, sym: Symbol):
        if sym.name in self.symbols:
            raise SemanticError(f"Variável '{sym.name}' já declarada em '{self.name}'")
        self.symbols[sym.name] = sym

    def lookup(self, name: str) -> Symbol | None:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name: str) -> Symbol | None:
        return self.symbols.get(name)


def implicit_type(name: str) -> str:
    """Regra IMPLICIT INTEGER (I-N) do Fortran."""
    return 'INTEGER' if name[0].upper() in 'IJKLMN' else 'REAL'


class SemanticAnalyzer:
    """
    Percorre a AST e realiza análises semânticas:
    - constrói tabelas de símbolos por âmbito
    - aplica tipagem implícita
    - resolve nós 'array_or_call' 
    - verifica usos inválidos (e.g. indexar escalar)
    """
    INTRINSICS = {
        'MOD'  : ('INTEGER', ['INTEGER', 'INTEGER']),
        'ABS'  : (None, [None]),      # polimórfico
        'IABS' : ('INTEGER', ['INTEGER']),
        'SQRT' : ('REAL', ['REAL']),
        'INT'  : ('INTEGER', [None]),
        'FLOAT': ('REAL', [None]),
        'MAX'  : (None, [None]),
        'MIN'  : (None, [None]),
    }

    def __init__(self):
        self.global_table = SymbolTable('global')
        self.current_table: SymbolTable = self.global_table
        self.current_function: str | None = None
        self.errors: list[str] = []

    def error(self, msg):
        self.errors.append(msg)
        print(f"[Semântica] ERRO: {msg}")

    # ------------------------------------------------------------------
    def analyze(self, ast):
        """
        Ponto de entrada da análise semântica.
        Executa em dois passos:
        1. Regista assinaturas de todas as funções/subroutines na
            tabela global, para suportar chamadas forward-reference.
        2. Analisa o corpo de cada unidade de programa.
        """
        if ast is None:
            return
        #1.
        for unit in ast.get('units', []):
            if unit['kind'] == 'function':
                sym = Symbol(unit['name'],
                            unit.get('ret_type') or implicit_type(unit['name']),
                            is_function=True, params=unit['params'],
                            ret_type=unit.get('ret_type') or implicit_type(unit['name']))
                try:
                    self.global_table.declare(sym)
                except SemanticError:
                    pass
            elif unit['kind'] == 'subroutine':
                sym = Symbol(unit['name'], 'VOID',
                            is_function=True, params=unit['params'])
                try:
                    self.global_table.declare(sym)
                except SemanticError:
                    pass
        # 2.
        for unit in ast.get('units', []):
            self._unit(unit)

    # ------------------------------------------------------------------
    def _unit(self, u):
        kind = u['kind']
        if kind == 'main_program':
            self.current_table = SymbolTable(u['name'], self.global_table)
            self.current_function = None
            self._stmts(u['body'])
            u['symtable'] = self.current_table
            self.current_table = self.global_table

        elif kind == 'function':
            sym = Symbol(u['name'], u.get('ret_type') or implicit_type(u['name']),
                         is_function=True, params=u['params'],
                         ret_type=u.get('ret_type') or implicit_type(u['name']))
            try:
                self.global_table.declare(sym)
            except SemanticError:
                pass        
            scope = SymbolTable(u['name'], self.global_table)
            self.current_table = scope
            self.current_function = u['name']
            # parâmetros
            for p in u['params']:
                psym = Symbol(p, implicit_type(p), is_param=True)
                scope.declare(psym)
            # variável de retorno (mesmo nome da função)
            ret_sym = Symbol(u['name'], sym.ret_type)
            scope.declare(ret_sym)
            self._stmts(u['body'])
            u['symtable'] = scope
            self.current_table = self.global_table
            self.current_function = None

        elif kind == 'subroutine':
            sym = Symbol(u['name'], 'VOID', is_function=True, params=u['params'])
            try:
                self.global_table.declare(sym)
            except SemanticError:
                pass    
            scope = SymbolTable(u['name'], self.global_table)
            self.current_table = scope
            self.current_function = None
            for p in u['params']:
                psym = Symbol(p, implicit_type(p), is_param=True)
                scope.declare(psym)
            self._stmts(u['body'])
            u['symtable'] = scope
            self.current_table = self.global_table

    # ------------------------------------------------------------------
    def _stmts(self, stmts):
        for s in stmts:
            if s is not None:
                self._stmt(s)

    # ------------------------------------------------------------------
    def _stmt(self, s):
        kind = s['kind']
        if kind == 'declaration':
            for v in s['vars']:
                size_expr = v.get('array_size')
                size = None
                if size_expr:
                    size = self._const_int(size_expr)
                # Se já declarado (e.g. parâmetro), atualizar tipo
                existing = self.current_table.lookup_local(v['name'])
                if existing is not None:
                    existing.dtype = s['dtype']
                    if size_expr:
                        existing.is_array = True
                        existing.array_size = size
                    continue
                sym = Symbol(v['name'], s['dtype'],
                             is_array=size_expr is not None,
                             array_size=size)
                try:
                    self.current_table.declare(sym)
                except SemanticError as e:
                    self.error(str(e))

        elif kind == 'assign':
            target_sym = self._ensure_var(s['target'])
            if s['index'] is not None:
                self._expr(s['index'])
                if target_sym and not target_sym.is_array:
                    self.error(f"'{s['target']}' não é um array")
            self._expr(s['value'])

        elif kind == 'print':
            for item in s['items']:
                self._expr(item)

        elif kind == 'read':
            for item in s['items']:
                if isinstance(item, dict) and item['kind'] == 'array_ref':
                    self._ensure_var(item['name'])
                    self._expr(item['index'])
                else:
                    self._ensure_var(item)

        elif kind == 'if':
            self._expr(s['cond'])
            self._stmts(s['then_body'])
            self._stmts(s['else_body'])

        elif kind == 'if_inline':
            self._expr(s['cond'])
            if s['stmt']:
                self._stmt(s['stmt'])

        elif kind == 'do':
            self._ensure_var(s['var'])
            self._expr(s['start'])
            self._expr(s['end'])
            if s['step']:
                self._expr(s['step'])
            self._stmts(s['body'])

        elif kind == 'call':
            sym = self.global_table.lookup(s['name'])
            if sym is None:
                # aceitar chamadas a subprogramas definidos à frente
                pass
            for a in s['args']:
                self._expr(a)

        elif kind in ('goto', 'continue', 'stop', 'return', 'label_only'):
            pass

    # ------------------------------------------------------------------
    def _ensure_var(self, name) -> Symbol | None:
        """Garante que a variável existe; cria implicitamente se necessário."""
        sym = self.current_table.lookup(name)
        if sym is None:
            sym = Symbol(name, implicit_type(name))
            self.current_table.declare(sym)
        return sym

    # ------------------------------------------------------------------
    def _expr(self, e):
        """
        Analisa uma expressão e devolve o seu tipo ('INTEGER', 'REAL', etc.).
        Como efeito lateral, resolve nós 'array_or_call' na AST.
        """
        if e is None:
            return 'INTEGER'
        kind = e['kind']

        if kind == 'INT_LIT':
            return 'INTEGER'
        if kind == 'FLOAT_LIT':
            return 'REAL'
        if kind == 'STR_LIT':
            return 'CHARACTER'
        if kind == 'BOOL_LIT':
            return 'LOGICAL'

        if kind == 'id':
            sym = self._ensure_var(e['name'])
            return sym.dtype if sym else 'INTEGER'

        if kind == 'binop':
            lt = self._expr(e['left'])
            rt = self._expr(e['right'])
            op = e['op']
            if op in ('.EQ.', '.NE.', '.LT.', '.LE.', '.GT.', '.GE.',
                      '.AND.', '.OR.'):
                return 'LOGICAL'
            if lt == 'REAL' or rt == 'REAL':
                return 'REAL'
            return 'INTEGER'

        if kind == 'unop':
            return self._expr(e['operand'])

        if kind == 'array_or_call':
            # Verifica se é array ou função?
            sym = self.current_table.lookup(e['name'])
            gsym = self.global_table.lookup(e['name'])
            if gsym and gsym.is_function:
                e['kind'] = 'func_call'
                e['args'] = [e.pop('index_or_args')]
                return gsym.ret_type or 'INTEGER'
            else:
                e['kind'] = 'array_ref'
                e['index'] = e.pop('index_or_args')
                if sym is None:
                    sym = self._ensure_var(e['name'])
                return sym.dtype if sym else 'INTEGER'

        if kind == 'array_ref':
            sym = self._ensure_var(e['name'])
            self._expr(e['index'])
            return sym.dtype if sym else 'INTEGER'

        if kind == 'func_call':
            for a in e['args']:
                self._expr(a)
            sym = self.global_table.lookup(e['name'])
            if sym:
                return sym.ret_type or 'INTEGER'
            return implicit_type(e['name'])

        if kind == 'intrinsic':
            for a in e['args']:
                self._expr(a)
            info = self.INTRINSICS.get(e['name'])
            return info[0] if info and info[0] else 'REAL'

        return 'INTEGER'

    # ------------------------------------------------------------------
    def _const_int(self, expr) -> int | None:
        if expr and expr['kind'] == 'INT_LIT':
            return expr['value']
        return None


def analyze(ast):
    """
    Executa a análise semântica sobre a AST e devolve o analisador
    com a tabela de símbolos preenchida, para uso pelo codegen.
    """
    sa = SemanticAnalyzer()
    sa.analyze(ast)
    return sa
