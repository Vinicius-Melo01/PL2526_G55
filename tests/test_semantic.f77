C Teste semantico: tipagem implicita e coercao
      PROGRAM TESTSEM
C N e implicito INTEGER (comeca por N)
C RESULT e implicito REAL (comeca por R)
      INTEGER N
      REAL RESULT
C Variavel implicita: X sera REAL por tipagem implicita
      N = 7
      RESULT = 0.0
C Coercao INTEGER -> REAL numa expressao mista
      RESULT = N * 1.5
C Uso de variavel nao declarada (tipagem implicita: SOMA -> REAL)
      SOMA = RESULT + 2.0
C Funcao intrinseca com coercao
      N = INT(SOMA)
      RESULT = FLOAT(N) / 3.0
      PRINT *, N, RESULT, SOMA
      END