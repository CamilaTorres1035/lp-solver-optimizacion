# Método de la Gran M (Big M) — Ejemplo Resuelto

## Documento de referencia para validar la implementación en BigMSimplexSolver

Resolver el siguiente modelo de Programación Lineal:   
min ⁡Z=2x1+3x2

x1+ x2 \>= 4  
x1+ 3x2 \<= 9  
x1, x2 \>= 0

1. Llevar a forma estándar  
   Como el problema es de minimización, se convierte a maximización resolviendo el problema equivalente:  
   	max \-⁡Z=-2x1-3x2  
   Se añaden variables de holgura (+Si), exceso (-Si) y artificiales (+Ri) según el tipo de restricción:  
   	x1+ x2 \- S1 \+ R1 \= 4  
   x1+ 3x2 \+ S2 \= 9  
   Nueva función objetivo  
   	max \-Z \= \-2x1-3x2-MR1  
   Reescrito en ecuación  
   \-Z \+ 2x1 \+ 3x2 \+ MR1= 0  
     
2. Tableau inicial  
   

|  | Z | x1 | x2 | S1 | R1 | S2 | RHS |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| (0) | \-1 | 2 | 3 | 0 | M | 0 | 0 |
| (1) R1 | 0 | 1 | 1 | \-1 | 1 | 0 | 4 |
| (2) S2 | 0 | 1 | 3 | 0 | 0 | 1 | 9 |

   

   La variable artificial R1 es básica (está en la base inicial), pero su coeficiente en la fila 0 es M. Para cumplir la condición de que toda variable básica tenga coeficiente cero en la fila 0, se aplica la operación (0) \- M(1) 

|  | Z | x1 | x2 | S1 | R1 | S2 | RHS |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| (0) | \-1 | 2-M | 3-M | M | 0 | 0 | \-4M |
| (1) R1 | 0 | 1 | 1 | \-1 | 1 | 0 | 4 |
| (2) S2 | 0 | 1 | 3 | 0 | 0 | 1 | 9 |

3. Iteraciones

	Variable que entra: coeficiente más negativo en (0)  
variable que sale: razón mínima positiva entre RHS y coeficientes de la columna de entrada

|  | Z | x1 | x2 | S1 | R1 | S2 | RHS |  |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| (0) | \-1 | 2-M | 3-M | M | 0 | 0 | \-4M |  |
| (1) R1 | 0 | 1 | 1 | \-1 | 1 | 0 | 4 | 4 |
| (2) S2 | 0 | 1 | 3 | 0 | 0 | 1 | 9 | 9 |

x1 y x2 tienen el mismo coeficiente de M, se desempata con su constante real (2 \< 3\) por tanto entra x1

(0) \- (2-M)(1)  
(2) \- (1)

|  | Z | x1 | x2 | S1 | R1 | S2 | RHS |  |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| (0) | \-1 | 0 | 1 | 2 | M-2 | 0 | \-8 |  |
| (1) R1 | 0 | 1 | 1 | \-1 | 1 | 0 | 4 | 4 |
| (2) S2 | 0 | 0 | 2 | 1 | \-1 | 1 | 5 |  |

No hay coeficientes negativos en (0) → se alcanzó la optimalidad del Simplex  
No hay variables artificiales con valor en la base → Solución factible

4. Solución Óptima

   x1 \= 4, x2 \= 0, Z \= 8

   Este procedimiento manual está respaldado por los siguientes tests unitarios:

   TestGranMArtificiales.test\_ejemplo\_a\_mano\_min — reproduce exactamente este ejemplo.

   TestGranMArtificiales.test\_dieta\_camino\_y\_resultado — verifica el camino de pivotes y el estado final.

   TestGranMArtificiales.test\_dieta\_fila\_0\_iteracion\_0 — valida los coeficientes simbólicos a+bM de la fila 0 inicial.