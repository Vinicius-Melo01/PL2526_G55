C Teste sintatico: todas as construcoes gramaticais
      PROGRAM TESTPARSER
      INTEGER A, B, C, NUMS(3)
      REAL X
      LOGICAL OK
C Declaracoes e atribuicoes
      A = 10
      B = 3
      X = 2.5
      OK = .FALSE.
C IF-THEN-ELSE
      IF (A .GT. B) THEN
        C = A - B
      ELSE
        C = B - A
      ENDIF
C IF inline
      IF (C .EQ. 0) STOP
C DO com passo
      DO 10 A = 1, 3
        NUMS(A) = A * 2
  10  CONTINUE
C GOTO
      B = 0
  20  IF (B .LT. 3) THEN
        B = B + 1
        GOTO 20
      ENDIF
      PRINT *, C, B, NUMS(1), NUMS(2), NUMS(3)
      END