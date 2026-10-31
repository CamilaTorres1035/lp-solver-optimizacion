# Solver de Programación Lineal

Aplicación interactiva para resolver problemas de **Programación Lineal (PL)** con visualización paso a paso del procedimiento de resolución.

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/Plotly-3F4F75?style=flat&logo=plotly&logoColor=white" alt="Plotly">
</div>

## Características

- **Método Gráfico** (2 variables): visualización interactiva de la región factible, vértices y recta de isoutilidad.
- **Método Símplex Gran M**: resolución algebraica completa para modelos con restricciones ≤, ≥ e =.
- **Método Símplex Revisado** *(opcional, sujeto a disponibilidad)*: validación cruzada del Gran M mediante operaciones matriciales exactas.
- **Aritmética exacta**: todos los cálculos se realizan con fracciones (`fractions.Fraction`), eliminando errores de redondeo.
- **M simbólico**: el valor M del Gran M se trata como un símbolo algebraico (`a + bM`), no como un número arbitrariamente grande.
- **Análisis de sensibilidad**: costos reducidos, precios sombra y rangos de optimalidad/factibilidad.
- **Navegación interactiva**: avanza y retrocede entre las iteraciones del Símplex sin recalcular.
- **Exportación**: descarga del procedimiento completo en un archivo de texto (.txt) generado en memoria.
- **Ejemplos precargados**: problemas clásicos de clase (Wyndor, dieta, casos especiales como degeneración o no acotados).

## Requisitos

- **Python 3.10+**
- Las dependencias se listan en `requirements.txt`:
  - `streamlit` — interfaz gráfica
  - `plotly` — gráficas interactivas 2D

> **Nota**: Todo lo demás es **biblioteca estándar de Python** (`fractions`, `dataclasses`, `typing`, `enum`, `unittest`, `io`), cumpliendo con la restricción de mínimas dependencias externas.

## Instalación

1. Clona el repositorio:

   ```bash
   git clone <url-del-repositorio>
   cd lp-solver-optimizacion
   ```

2. Crea y activa un entorno virtual:

   ```bash
   python -m venv .venv
   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   # Linux / macOS
   source .venv/bin/activate
   ```

3. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

## Ejecución

### Aplicación Streamlit

```bash
streamlit run src/presentation/app.py
```

La aplicación se abrirá automáticamente en el navegador (por defecto en `http://localhost:8501`).

### Pruebas unitarias

```bash
# Ejecutar todas las pruebas
python -m unittest discover -s tests -v

# Ejecutar un módulo específico
python -m unittest tests/domain/test_linalg.py -v
python -m unittest tests/domain/test_symbolic.py -v

# Stress test de rendimiento
python -m unittest tests/test_performance.py -v
```

## Estructura del proyecto

```txt
.
├── src/
│   ├── application/         # Casos de uso y orquestación
│   │   ├── use_cases/       # validate_model, solve_lp, analyze_sensitivity, export_summary
│   │   └── __init__.py
│   ├── domain/              # Lógica de negocio pura (Python puro, sin dependencias externas)
│   │   ├── model/           # LPModel, Constraint, ObjectiveFunction, Builder
│   │   ├── sensitivity/     # SensitivityAnalyzer
│   │   ├── solver/          # Protocol Solver, Gran M, Revisado, Gráfico, ValorM, linalg
│   │   ├── validation/      # ModelValidator
│   │   └── __init__.py
│   ├── presentation/        # Interfaz Streamlit (única capa que conoce la UI)
│   │   ├── components/      # Tableau, navegación, gráficas
│   │   ├── tabs/            # Pestañas: modelo, resolver, sensibilidad, exportar
│   │   ├── __init__.py
│   │   └── app.py           # Punto de entrada de Streamlit
│   ├── utils/               # Utilidades transversales (formateo, ejemplos precargados)
│   └── __init__.py
├── tests/                   # Pruebas unitarias y de rendimiento
│   ├── application/
│   ├── domain/
│   ├── __init__.py
│   └── test_performance.py
├── .gitattributes
├── .gitignore
├── README.md
└── requirements.txt
```

## Decisiones técnicas clave

1. **Aritmética exacta con `fractions.Fraction`**: evita errores de redondeo y garantiza resultados reproducibles.
2. **M simbólico (`ValorM`)**: representa `a + bM` sin usar un número grande.
3. **Inmutabilidad total**: `@dataclass(frozen=True)` y tuplas en lugar de listas.
4. **Iteraciones precalculadas**: el solver calcula todos los pasos de una vez, permitiendo navegación instantánea.
5. **Operación en memoria**: no hay persistencia; el estado se maneja con `st.session_state`.

## Estado del proyecto

| Sprint | Estado | Entregable |
|--------|--------|------------|
| **Sprint 0** | Completado | Tipos de dominio, `ValorM`, `linalg`, esqueleto ejecutable, pruebas de rendimiento |
| **Sprint 1** | En progreso | Modelo, validación, estado, método gráfico, navegación |
| **Sprint 2** | Pendiente | Símplex Gran M, casos especiales, Símplex Revisado (Si hay tiempo) |
| **Sprint 3** | Pendiente | Análisis de sensibilidad, exportación |

## Equipo/Autores

- **Camila Torres Chica**
- **Daniel Sanchez Escobar**
- **Jesica Estor Soto**

## Referencias

- Taha, H. A. (2017). *Investigación de Operaciones*. Pearson Educación.
- Hillier, F. S., & Lieberman, G. J. (2010). *Introducción a la Investigación de Operaciones*. McGraw-Hill.
- Martin, R. C. (2018). *Clean Architecture*. Prentice Hall.
- Ortiz, R. A. *Investigación de Operaciones I* (diapositivas de clase, UdeA).

---

<div align="center">
Proyecto académico — Optimización — Universidad de Antioquia.
</div>
