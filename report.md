# Compilador Fortran 77

Unidade Curricular de Processamento de Linguagens — Ano Letivo 2025/2026

Trabalho Prático - Grupo 55

| Nome | Número |
|------|--------|
| Vinicius Melo | a101926 |
| João Costa | a84701 |
| Pedro Figueiredo | a104354 |

Maio, 2026

---

## Índice

1. [Introdução](#1-introdução)
2. [Arquitetura do Compilador](#2-arquitetura-do-compilador)
3. [Análise Léxica](#3-análise-léxica)
4. [Análise Sintática](#4-análise-sintática)
5. [Análise Semântica](#5-análise-semântica)
6. [Geração de Código](#6-geração-de-código)
7. [Testes e Resultados](#7-testes-e-resultados)
8. [Instruções de Uso](#8-instruções-de-uso)
9. [Conclusão](#9-conclusão)

---

## 1. Introdução

Este relatório descreve o desenvolvimento de um compilador para a linguagem Fortran 77, realizado no âmbito da unidade curricular de Processamento de Linguagens.

O objetivo do projeto é implementar um compilador completo que traduza código Fortran 77 para um código executável pela máquina virtual EWVM, uma máquina de pilha disponibilizada para a unidade curricular. O compilador foi implementado em Python, recorrendo à biblioteca PLY (Python Lex-Yacc) para as fases de análise léxica e sintática.

O compilador suporta o subconjunto essencial da linguagem: declarações de tipos (`INTEGER`, `REAL`, `LOGICAL`, `CHARACTER`), expressões aritméticas, relacionais e lógicas, controlo de fluxo (`IF-THEN-ELSE`, ciclos `DO` com labels, `GOTO`), operações de I/O (`READ`, `PRINT`), arrays unidimensionais e por fim definição e invocação de subprogramas (`FUNCTION` e `SUBROUTINE`).

O grupo optou por suportar o formato de colunas fixas do Fortran 77, em que as colunas 1-5 reservam-se a labels numéricos, a coluna 6 indica continuação de linha, e as colunas 7-72 contêm o código-fonte.

---

## 2. Arquitetura do Compilador

O compilador segue o pipeline clássico de tradução de linguagens, organizado em quatro fases sequenciais, cada uma implementada num módulo Python independente:

```
Ficheiro .f77
      |
      v
[1. PRE-PROCESSADOR]  (lexer.py: preprocess_fixed_form)
  - Remove comentarios (col 1: C, *, !)
  - Colapsa linhas de continuacao (col 6)
  - Codifica labels como #n#
      | texto limpo com marcadores #label#
      v

[2. ANALISE LEXICA]  (lexer.py)
  - ply.lex + expressoes regulares
  - Produz sequencia de tokens (PROGRAM, ID, INT_LIT, IF, ...)
      | sequencia de tokens
      v
[3. ANALISE SINTATICA]  (parser.py)
  - ply.yacc LALR(1)
  - Valida estrutura gramatical
  - Constroi AST (dicionarios Python)
      | AST (Abstract Syntax Tree)
      v
[4. ANALISE SEMANTICA]  (semantic.py)
  - Constroi tabela de simbolos por ambito
  - Aplica tipagem implicita (I-N -> INTEGER)
  - Resolve nos array_or_call
  - Verifica erros semanticos
  - Anota AST in-place
      | AST anotada + tabela de simbolos
      v
[5. GERACAO DE CODIGO]  (codegen.py)
  - Percorre AST anotada
  - Atribui offsets as variaveis
  - Emite instrucoes EWVM
  - Gere labels e controlo de fluxo
      | codigo EWVM
      v
Ficheiro .vm
```

O módulo `compiler.py` serve de ponto de entrada (CLI), orquestrando as quatro fases e expondo flags de debug (`--tokens`, `--ast`).

### 2.1. Pré-processador

Antes da análise léxica, o código fonte em formato fixo é normalizado pela função `preprocess_fixed_form`. Esta função elimina linhas de comentário (coluna 1 com `C`, `*` ou `!`), colapsa linhas de continuação (coluna 6 diferente de espaço ou `0`) e codifica os labels numéricos (colunas 1 a 5) como marcadores inline na forma `#label#`, reservando a sua associação com a instrução que anotam sem necessitar de um passo separado de resolução de labels. O pré-processamento está integrado no módulo `lexer.py` e é invocado automaticamente antes da tokenização.

Esta abordagem evita a necessidade de um modo léxico especial ou de um pré-processador externo, mantendo todo o tratamento do formato fixo num único passo de transformação de texto.

### 2.2. A AST como Interface entre Fases

A Abstract Syntax Tree (AST) é a estrutura de dados central que serve de contrato entre as fases de análise sintática, semântica e geração de código. É representada como um grafo de dicionários Python aninhados, em que cada nó tem obrigatoriamente um campo `kind` que identifica o tipo de construção (e.g., `'assign'`, `'if'`, `'do'`, `'binop'`).

Esta escolha permite que cada fase percorra a AST de forma independente, e que a fase semântica a anote in-place, por exemplo, resolvendo nós ambíguos `array_or_call` para `array_ref` ou `func_call`, e adicionando a tabela de símbolos (`symtable`) a cada unidade de programa, sem que as restantes fases precisem de conhecer os detalhes internos da análise semântica.

---

## 3. Análise Léxica

A análise léxica foi implementada no módulo `lexer.py` com recurso à biblioteca `ply.lex`, que constrói um autómato finito determinista a partir de expressões regulares associadas a cada token, correspondendo ao modelo teórico de linguagens regulares estudado na unidade curricular.

### 3.1. Tokens Reconhecidos

| Categoria | Tokens |
|-----------|--------|
| Palavras-chave | `PROGRAM`, `END`, `IF`, `THEN`, `ELSE`, `ENDIF`, `DO`, `CONTINUE`, `GOTO`, `READ`, `PRINT`, `STOP`, `RETURN`, `CALL`, `SUBROUTINE`, `FUNCTION` |
| Tipos | `INTEGER`, `REAL`, `LOGICAL`, `CHARACTER` |
| Funções intrínsecas | `MOD`, `ABS`, `IABS`, `SQRT`, `INT`, `FLOAT`, `MAX`, `MIN` |
| Literais | `INT_LIT`, `FLOAT_LIT`, `STR_LIT`, `BOOL_LIT` |
| Operadores relacionais | `.EQ.`, `.NE.`, `.LT.`, `.LE.`, `.GT.`, `.GE.` |
| Operadores lógicos | `.AND.`, `.OR.`, `.NOT.` |
| Operadores aritméticos | `+`, `-`, `*`, `/`, `**` |
| Especiais | `LABEL`, `NEWLINE`, `(`, `)`, `,`, `=` |

As palavras-chave são identificadas dentro da regra do token `ID`: qualquer sequência alfanumérica é primeiro reconhecida como identificador e depois consultada num dicionário `reserved`; se existir, o tipo do token é substituído pelo da palavra-chave correspondente. Todos os identificadores e palavras-chave são convertidos para maiúsculas, respeitando a insensibilidade a maiúsculas/minúsculas do Fortran 77.

---

## 4. Análise Sintática

A análise sintática foi implementada no módulo `parser.py` com recurso à biblioteca `ply.yacc`, que gera um analisador LALR(1) a partir das regras gramaticais definidas em Python. O parser constrói a AST diretamente durante a redução das regras, sem produzir uma árvore de derivação intermédia.

### 4.1. Gramática

A gramática está organizada hierarquicamente, do nível mais alto para o mais baixo:

Estrutura do programa:

```
program               -> program_unit_list
program_unit_list     -> program_unit
                      |  program_unit_list  program_unit
program_unit          -> main_program
                      |  function_subprogram
                      |  subroutine_subprogram
main_program          -> PROGRAM ID NEWLINE statement_list END
function_subprogram   -> type_spec FUNCTION ID ( param_list ) NEWLINE statement_list END
                      |  FUNCTION ID ( param_list ) NEWLINE statement_list END
subroutine_subprogram -> SUBROUTINE ID ( param_list ) NEWLINE statement_list END
param_list            -> ID
                      |  param_list , ID
                      |  ε
type_spec             -> INTEGER | REAL | LOGICAL | CHARACTER
```

Statements:

```
statement          -> LABEL unlabeled_stmt
                   |  unlabeled_stmt
unlabeled_stmt     -> declaration_stmt  | assignment_stmt
                   |  print_stmt        | read_stmt
                   |  if_stmt           | do_stmt
                   |  goto_stmt         | continue_stmt
                   |  stop_stmt         | return_stmt  | call_stmt
declaration_stmt   -> type_spec var_decl_list NEWLINE
var_decl_list      -> var_decl
                   |  var_decl_list , var_decl
var_decl           -> ID
                   |  ID ( expr )
assignment_stmt    -> ID = expr NEWLINE
                   |  ID ( expr ) = expr NEWLINE
print_stmt         -> PRINT * , print_items NEWLINE
print_items        -> expr
                   |  print_items , expr
read_stmt          -> READ * , read_items NEWLINE
read_items         -> ID
                   |  read_items , ID
                   |  ID ( expr )
continue_stmt      -> CONTINUE NEWLINE
stop_stmt          -> STOP NEWLINE
return_stmt        -> RETURN NEWLINE
call_stmt          -> CALL ID ( arg_list ) NEWLINE
```

Controlo de fluxo:

```
if_stmt   -> IF ( expr ) THEN NEWLINE statement_list ENDIF NEWLINE
           | IF ( expr ) THEN NEWLINE statement_list ELSE NEWLINE statement_list ENDIF NEWLINE
           | IF ( expr ) unlabeled_stmt
do_stmt   -> DO INT_LIT ID = expr , expr NEWLINE statement_list LABEL CONTINUE NEWLINE
           | DO INT_LIT ID = expr , expr , expr NEWLINE statement_list LABEL CONTINUE NEWLINE
goto_stmt -> GOTO INT_LIT NEWLINE
```

Expressões:

```
expr  -> expr .OR. expr
       | expr .AND. expr
       | .NOT. expr
       | expr relop expr
       | expr + expr  |  expr - expr
       | expr * expr  |  expr / expr
       | - expr
       | expr ** expr
       | ( expr )
       | INT_LIT | FLOAT_LIT | STR_LIT | BOOL_LIT
       | ID | ID ( expr ) | ID ( arg_list )
       | intrinsic_call
relop    -> .EQ. | .NE. | .LT. | .LE. | .GT. | .GE.
arg_list -> expr
          | arg_list , expr
```

A precedência de operadores é declarada explicitamente ao PLY através da tabela `precedence`, seguindo as regras do Fortran 77: operadores aritméticos têm precedência sobre os relacionais, que por sua vez têm precedência sobre os lógicos.

### 4.2. Construção da AST

Cada regra gramatical instancia um nó da AST através da função auxiliar `node(kind, **kwargs)`, que cria um dicionário com o campo `kind` e os atributos semânticos relevantes. Por exemplo:

```python
# Atribuição simples: X = expr
node('assign', target='X', index=None, value=<expr_node>)

# Ciclo DO
node('do', end_label=10, var='I', start=<expr>, end=<expr>, step=None, body=[...])

# IF com ELSE
node('if', cond=<expr>, then_body=[...], else_body=[...])
```

Os nós são compostos de forma recursiva durante as reduções LALR(1), produzindo uma árvore que reflecte fielmente a estrutura do programa fonte.

### 4.3. Ambiguidade: `array_or_call`

Uma limitação inerente ao Fortran 77 é que a sintaxe de acesso a array (`A(I)`) e de chamada de função (`F(X)`) é indistinguível durante a análise sintática, ambas têm a forma `ID ( expr )`. O parser produz sempre um nó intermédio `array_or_call` para esta construção, delegando a resolução para a fase semântica, que consulta a tabela de símbolos para determinar se o identificador é uma função ou um array.

### 4.4. Conflitos na Gramática LALR(1)

A gramática gerada apresenta 2 conflitos shift/reduce e 32 conflitos reduce/reduce, todos detetados e reportados pelo PLY durante a construção das tabelas LALR(1).

Os conflitos reduce/reduce têm origem na regra do ciclo `DO`: quando o parser encontra `LABEL CONTINUE` dentro do `statement_list` do corpo de um `DO`, não consegue determinar imediatamente se deve reduzi-lo como `labeled_statement` autónomo ou como terminador do `do_stmt`. O PLY resolve este conflito pela regra de primeira produção definida (neste caso correspondente ao `do_stmt`) o comportamento correto. Os conflitos shift/reduce resultam da ambiguidade do `RPAREN` em expressões com parênteses, resolvidos por shift, também correto.

Todos os conflitos são, portanto, resolvidos na direção semanticamente correta para os programas Fortran 77 suportados, e os cinco programas de teste compilam sem erros.

---

## 5. Análise Semântica

A análise semântica é implementada no módulo `semantic.py` e opera sobre a AST produzida pelo parser. O seu objetivo é verificar a coerência do programa para além da estrutura sintática, nomeadamente a declaração e uso de variáveis, a consistência de tipos, e a resolução de construções ambíguas deixadas pelo parser.

### 5.1. Tabela de Símbolos

A tabela de símbolos é implementada pela classe `SymbolTable`, com suporte a âmbitos aninhados. Cada âmbito mantém um dicionário de símbolos e um ponteiro para o âmbito pai, permitindo lookup hierárquico; uma variável não encontrada no âmbito atual é procurada recursivamente no âmbito envolvente.

Cada entrada na tabela é um objeto `Symbol` com os seguintes atributos:

| Atributo | Descrição |
|----------|-----------|
| `name` | Nome da variável ou subprograma |
| `dtype` | Tipo: `INTEGER`, `REAL`, `LOGICAL`, `CHARACTER` ou `VOID` |
| `is_array` | Indica se é array unidimensional |
| `array_size` | Tamanho do array (inteiro) ou `None` |
| `is_function` | Indica se é função ou subroutine |
| `offset` | Posição na pilha da VM, atribuída pelo gerador de código |
| `ret_type` | Tipo de retorno de uma função (`INTEGER`, `REAL`, etc.) ou `None` |
| `params` | Lista dos nomes dos parâmetros da função/subroutine |

O compilador mantém três âmbitos distintos: o âmbito global (funções e subroutines registadas), o âmbito do programa principal, e um âmbito por cada subprograma.

### 5.2. Tipagem Implícita

O Fortran 77 define uma regra de tipagem implícita: variáveis cujo nome começa pelas letras I a N são do tipo `INTEGER`; todas as restantes são `REAL`. Esta regra é implementada pela função `implicit_type` e aplicada sempre que uma variável é referenciada sem declaração explícita prévia, criando-a automaticamente na tabela de símbolos com o tipo inferido.

### 5.3. Dois Passos de Análise

A análise semântica executa em dois passos sobre a lista de unidades de programa:

1. Registo de assinaturas: todas as funções e subroutines são registadas na tabela global antes de qualquer análise de corpo. Isto permite suportar chamadas forward-reference; o programa principal pode chamar uma função definida depois dele no ficheiro fonte, como acontece no teste `conversor.f77`.

2. Análise dos corpos: cada unidade de programa é analisada individualmente, construindo o seu âmbito local, verificando declarações e usos de variáveis, e anotando a AST com a tabela de símbolos (`symtable`).

### 5.4. Resolução de `array_or_call`

Como descrito na secção anterior, o parser não consegue distinguir `A(I)` (acesso a array) de `F(X)` (chamada de função). A análise semântica resolve esta ambiguidade consultando a tabela global: se o identificador está registado como função, o nó `array_or_call` é convertido para `func_call`; caso contrário, é convertido para `array_ref`. Esta resolução é feita in-place na AST, alterando o campo `kind` do nó sem necessidade de reconstruir a árvore.

### 5.5. Verificações Implementadas

A análise semântica realiza as seguintes verificações, reportando erros sem abortar a compilação (permitindo detetar múltiplos erros numa só passagem):

- Declaração duplicada de variável no mesmo âmbito.
- Indexação de uma variável escalar como se fosse array.
- Uso de variáveis não declaradas (resolvido por tipagem implícita, sem erro).

---

## 6. Geração de Código

A geração de código é implementada no módulo `codegen.py` pela classe `CodeGenerator`, que percorre a AST anotada pela análise semântica e emite instruções para a máquina virtual EWVM , uma máquina de pilha em que todas as operações atuam sobre o topo da pilha (stack), sem registos de uso geral.

### 6.1. Convenções da VM

| Instrução | Base | Utilização |
|-----------|------|------------|
| `PUSHG` / `STOREG` | `gp` | Variáveis do programa principal |
| `PUSHL` / `STOREL` | `fp` | Variáveis locais de funções e subroutines |

A cada variável é atribuído um offset inteiro sequencial (campo `offset` do `Symbol`) durante a fase de geração de código, imediatamente antes de se gerar o corpo de cada unidade de programa. Para o programa principal, os offsets são atribuídos em ordem de inserção na tabela de símbolos; para subprogramas, os parâmetros recebem offsets negativos e as variáveis locais offsets não-negativos (ver secção de subprogramas).

### 6.2. Arrays

Arrays unidimensionais são alocados no heap da VM com a instrução `ALLOC n`, que reserva `n` posições contíguas e deixa no topo da pilha o endereço base do bloco. Este endereço é imediatamente guardado na variável correspondente (`STOREG` / `STOREL`).

O acesso a um elemento `A(I)` é feito em três passos:

1. Carregar o endereço base: `PUSHG offset_A`
2. Calcular o offset: `[push I]`, `PUSHI 1`, `SUB`: os índices Fortran começam em 1, pelo que o offset na VM é `I - 1`
3. Somar ao endereço base: `PADD`

A leitura usa `LOAD 0` e a escrita `STORE 0` sobre o endereço calculado.

### 6.3. Controlo de Fluxo

IF-THEN-ELSE: o gerador cria dois labels frescos (`ELSE_n` e `ENDIF_n`). A condição é avaliada e seguida de `JZ ELSE_n`; o corpo do `THEN` é emitido, depois `JUMP ENDIF_n`; o corpo do `ELSE` (se existir) é emitido após o label `ELSE_n`; o label `ENDIF_n` marca o fim da construção. Se não houver `ELSE`, o `ELSE_n` serve diretamente de label de fim.

Ciclo DO: o gerador inicializa a variável de controlo, emite o label de início do loop (`DO_n`), avalia a condição `var <= limite` com `INFEQ` e `JZ DOEND_n`. O label Fortran do `CONTINUE` é mapeado para um label VM (`FL_n`) que marca o ponto de incremento, imediatamente antes de `JUMP DO_n`, permitindo que `GOTO` dentro do corpo salte diretamente para o incremento.

GOTO: mapeado diretamente para `JUMP FL_n`, onde `FL_n` é o label VM correspondente ao label Fortran referenciado. O mapeamento é gerido por um dicionário `fortran_labels` que garante que o mesmo label Fortran produz sempre o mesmo label VM, independentemente da ordem em que é encontrado.

### 6.4. Subprogramas

A convenção de chamada adotada segue o modelo da EWVM:

1. O chamador empilha os argumentos por ordem.
2. O chamador executa `PUSHA label` seguido de `CALL`.
3. A instrução `CALL` cria uma nova frame; os argumentos ficam abaixo do novo `fp`.
4. Os parâmetros são acedidos com offsets negativos: para `n` parâmetros, o primeiro fica em `fp[-n]` e o último em `fp[-1]`.
5. As variáveis locais (incluindo a variável de retorno da função) ficam em `fp[0]`, `fp[1]`, ..., alocadas com `PUSHN k`.
6. O valor de retorno de uma função é guardado numa variável local com o mesmo nome da função (convenção Fortran). Antes de `RETURN`, este valor é empilhado com `PUSHL offset_ret`, ficando no topo após o retorno.
7. O chamador recebe o valor de retorno no topo da pilha após o `CALL`.

### 6.5. Tipos e Coerção

O gerador determina o tipo de cada sub-expressão através do método `_expr_type`, que percorre a AST sem emitir código. Quando uma operação aritmética envolve operandos de tipos mistos (`INTEGER` e `REAL`), o operando inteiro é promovido com `ITOF` antes da operação. As instruções usadas variam consoante o tipo: `ADD`/`FADD`, `SUB`/`FSUB`, `MUL`/`FMUL`, `DIV`/`FDIV`, `INF`/`FINF`, etc.

Para I/O, a instrução `READ` lê sempre uma string; a conversão para o tipo correto é feita com `ATOI` (inteiro) ou `ATOF` (real). Na impressão, são usadas `WRITEI`, `WRITEF` ou `WRITES` conforme o tipo da expressão, seguidas de `WRITELN` no final de cada `PRINT`.

### 6.6. Exemplo: Fatorial

Para ilustrar o código gerado, apresenta-se o excerto VM correspondente ao ciclo `DO` do programa `fatorial.f77` (variáveis: `N` -> offset 0, `I` -> 1, `FAT` -> 2):

```
PUSHI 1
STOREG 2       ; FAT = 1
PUSHI 1
STOREG 1       ; I = 1  (inicialização DO)
DO1:
PUSHG 1        ; I
PUSHG 0        ; N
INFEQ          ; I <= N
JZ DOEND2
PUSHG 2        ; FAT
PUSHG 1        ; I
MUL
STOREG 2       ; FAT = FAT * I
FL3:           ; label CONTINUE 10 (ponto de incremento)
PUSHG 1
PUSHI 1
ADD
STOREG 1       ; I = I + 1
JUMP DO1
DOEND2:
```

### 6.7. Otimização de Código

O compilador não implementa otimizações formais sobre a representação intermédia, uma vez que a AST é traduzida diretamente para código VM numa única passagem. Ainda assim, algumas decisões de geração contribuem para a qualidade do código produzido:

- A coerção de tipos (`ITOF`) é emitida apenas quando necessária, evitando conversões redundantes em expressões homogéneas.
- Labels Fortran são mapeados de forma lazy, i.e., só são criados quando referenciados, evitando labels mortos no código gerado.
- O pré-processador elimina comentários e linhas em branco antes da tokenização, reduzindo o trabalho das fases seguintes.

---

## 7. Testes e Resultados

Para validar o compilador, foram implementados cinco programas de teste em Fortran 77, correspondendo aos exemplos fornecidos no enunciado do projeto. Cada programa foi escolhido para exercitar um conjunto distinto de funcionalidades do compilador.

### 7.1. Programas de Teste

| Programa | Funcionalidades testadas | Resultado |
|----------|--------------------------|-----------|
| `hello.f77` | Estrutura mínima do programa, `PRINT` com literal de string | OK |
| `fatorial.f77` | Declarações `INTEGER`, `READ`, ciclo `DO`, atribuição, `PRINT` com múltiplos itens | OK |
| `primo.f77` | `LOGICAL`, `IF-THEN-ELSE`, `GOTO` para label em `IF` (não `DO`), `.AND.`, `MOD` | OK |
| `somaarr.f77` | Array unidimensional, `ALLOC`, `PADD`, `READ`/`PRINT` com elementos de array | OK |
| `conversor.f77` | `INTEGER FUNCTION`, `CALL`, passagem de argumentos, `RETURN`, forward-reference | OK |

Todos os programas compilam sem erros e produzem código VM sintaticamente correto. O script `run_tests.sh` automatiza a compilação de todos os testes e deposita os ficheiros `.vm` gerados na pasta `output/`.

Para além dos cinco programas do enunciado, foram desenvolvidos quatro testes adicionais com o objetivo de exercitar explicitamente cada fase do compilador:

| Programa | Fase testada / Objetivo | Resultado |
|----------|-------------------------|-----------|
| `test_lexer.f77` | Léxico: literais de todos os tipos, notação científica, operadores relacionais e lógicos, continuação de linha | OK |
| `test_parser.f77` | Sintático: todas as construções gramaticais num único programa, `IF-THEN-ELSE`, `IF` inline, `DO`, `GOTO` com label em `IF`, acesso a array | OK |
| `test_semantic.f77` | Semântico: tipagem implícita, coerção automática `INTEGER` -> `REAL` (`ITOF`), conversões explícitas `INT()` e `FLOAT()`, variáveis criadas implicitamente | OK |
| `test_codegen.f77` | Geração de código: array no heap, chamada de função com dois argumentos, `MOD`, `ABS`, offsets negativos para parâmetros | OK |

### 7.2. Limitações Conhecidas

| Construção | Motivo |
|------------|--------|
| `**` (potência) | Sem instrução nativa na EWVM |
| `SQRT` | Sem instrução nativa na EWVM |
| `MAX` / `MIN` | Não implementado; não é usado nos testes |
| Passagem por referência | Parâmetros passados por valor (simplificação) |
| `FORMAT`, `WRITE`, `COMMON` | Fora do âmbito do projeto |

---

## 8. Instruções de Uso

### 8.1. Requisitos

O compilador requer Python 3.10 ou superior e a biblioteca `ply`, instalável via:

```bash
pip install ply
```

### 8.2. Compilação de um Programa

```bash
# Compilar e imprimir código VM no terminal
python3 compiler.py tests/hello.f77

# Guardar o código VM num ficheiro
python3 compiler.py tests/fatorial.f77 -o output/fatorial.vm
```

### 8.3. Opções Disponíveis

| Flag | Descrição |
|------|-----------|
| `-o <ficheiro>` | Escreve o código VM gerado no ficheiro indicado |
| `--tokens` | Imprime a sequência de tokens produzida pelo lexer (debug léxico) |
| `--ast` | Imprime a AST produzida pelo parser (debug sintático) |
| `--free` | Interpreta o ficheiro de entrada em formato livre em vez de colunas fixas |

### 8.4. Executar Todos os Testes

O script `run_tests.sh` compila todos os programas de teste e deposita os ficheiros `.vm` gerados na pasta `output/`:

```bash
bash run_tests.sh
```

---

## 9. Conclusão

Este projeto consistiu no desenvolvimento de um compilador completo para um subconjunto significativo do Fortran 77, cobrindo todas as etapas do pipeline de compilação: análise léxica, análise sintática, análise semântica e geração de código para a máquina virtual EWVM.

O compilador processa corretamente os cinco programas de teste fornecidos no enunciado, incluindo construções como ciclos `DO` com labels, `GOTO`, arrays unidimensionais, expressões lógicas e relacionais, e subprogramas (`FUNCTION` e `SUBROUTINE`) como funcionalidade de valorização.

Do ponto de vista técnico, as principais decisões de implementação foram:

- Suporte ao formato de colunas fixas do Fortran 77, resolvido por um pré-processador dedicado antes da tokenização.
- Representação da AST como dicionários Python aninhados, servindo de contrato entre as fases e permitindo anotação in-place pela análise semântica.
- Resolução da ambiguidade `array_or_call` delegada para a análise semântica, que consulta a tabela de símbolos para distinguir acesso a array de chamada de função.
- Convenção de chamada com parâmetros em offsets negativos relativos a `fp`, seguindo o modelo da EWVM.
- Dois passos de análise semântica para suportar chamadas forward-reference a subprogramas definidos após o programa principal.

As principais limitações do compilador são a ausência de suporte ao operador de potência `**` e à função `SQRT` (sem instrução nativa na EWVM), a passagem de parâmetros exclusivamente por valor, e a não implementação de otimizações sobre o código gerado, opção válida e explicitamente prevista no enunciado, que permite tradução direta sem representação intermédia.