C Teste codegen: arrays, funcoes e subrotinas
      PROGRAM TESTCODEGEN
      INTEGER N, I, RES, MAXVAL
      INTEGER NUMS(5)
      N = 5
      DO 10 I = 1, N
        NUMS(I) = I * I
  10  CONTINUE
C Chamada a funcao com 2 argumentos
      MAXVAL = MAIOR(NUMS(1), NUMS(5))
      PRINT *, 'Maior entre', NUMS(1), 'e', NUMS(5), ':', MAXVAL
C MOD e ABS
      RES = MOD(NUMS(3), 2)
      PRINT *, 'MOD(9,2) =', RES
      RES = ABS(-42)
      PRINT *, 'ABS(-42) =', RES
      END

      INTEGER FUNCTION MAIOR(A, B)
      INTEGER A, B
      IF (A .GT. B) THEN
        MAIOR = A
      ELSE
        MAIOR = B
      ENDIF
      RETURN
      END