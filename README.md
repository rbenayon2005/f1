# F1 - Resultados y calendario

Script en Python que consulta la API pública [Jolpica-F1 / Ergast](https://api.jolpi.ca/ergast/) para mostrar el calendario de la temporada de Fórmula 1 y los resultados de cada carrera.

## Instalación

Requiere Python 3.9+.

```bash
cd f1
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Uso

### Última carrera corrida

Sin parámetros, muestra el resultado de la última carrera ya finalizada del año en curso.

```bash
source venv/bin/activate
python3 efeuno.py
```

### Calendario de la temporada

Con el parámetro `circuitos`, muestra el calendario completo del año en curso: fecha, Gran Premio, circuito y si ya se corrió (✓).

```bash
source venv/bin/activate
python3 efeuno.py circuitos
```

Para ver el calendario de un año específico, añade el año como segundo parámetro:

```bash
source venv/bin/activate
python3 efeuno.py circuitos 2024
python3 efeuno.py circuitos 1999
```

### Resultado de una carrera puntual

Pasando el nombre de un circuito, Gran Premio, ubicación o país (tal como figura en el listado de `circuitos`), muestra el resultado de esa carrera puntual. Si todavía no se corrió, informa la fecha programada en lugar de un resultado.

```bash
source venv/bin/activate
python3 efeuno.py "belgian"
python3 efeuno.py "hungaroring"
python3 efeuno.py "imola" 1999
```

Para buscar en un año específico, añade el año como segundo parámetro:

```bash
source venv/bin/activate
python3 efeuno.py "belgian" 2024
python3 efeuno.py "imola" 1999
```

**Nota:** La API Jolpica-F1 tiene cobertura histórica mucho más amplia y permite consultar temporadas desde 1950 en adelante.

La búsqueda no distingue mayúsculas/minúsculas y admite coincidencias parciales.

## Qué muestra el resultado de una carrera

Para cada carrera se listan los pilotos ordenados por posición final, con:

- **Pos.**: posición final
- **Auto**: número de auto
- **Piloto**: nombre completo
- **Escudería**: equipo
- **Salida**: posición de largada
- **Cambio**: variación de posiciones entre la largada y la llegada (▲ subió, ▼ bajó, `=` sin cambios)
