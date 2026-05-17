C Teste lexico: literais, operadores, continuacao de linha
      PROGRAM TESTLEX
      INTEGER I
      REAL X
      LOGICAL FLAG
C Literais de varios tipos
      I = 42
      X = 3.14
      FLAG = .TRUE.
C Operadores relacionais e logicos
      IF (I .GE. 0 .AND. .NOT. FLAG) THEN
        X = -1.5E2
      ENDIF
C Linha com continuacao
      I = 1 +
     &    2 +
     &    3
      PRINT *, I, X, FLAG
      END