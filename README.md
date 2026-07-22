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

### Historial de ganadores de un circuito

Pasando el nombre de un circuito (id, nombre, localidad o país) y `all` como segundo parámetro, muestra el ganador de cada año que se corrió en ese circuito a lo largo de toda la historia.

```bash
source venv/bin/activate
python3 efeuno.py hungaroring all
python3 efeuno.py silverstone all
```

Si la búsqueda coincide con más de un circuito, se listan las coincidencias para repetir la búsqueda con un dato más específico.

### Posiciones de un piloto

Si el primer parámetro no coincide con ningún circuito, se interpreta como el nombre o apellido de un piloto y se muestran sus resultados carrera por carrera.

```bash
source venv/bin/activate
python3 efeuno.py "Alonso"        # temporada actual
python3 efeuno.py "Alonso" 2012   # una temporada puntual
python3 efeuno.py "Alonso" all    # toda su carrera
```

Si no se indica año, se intenta primero con la temporada actual; si el piloto no corrió ese año (por ejemplo, un piloto retirado como "Fangio"), se muestra automáticamente toda su carrera. Si se indica un año puntual y el piloto no corrió ese año, se informa el error en lugar de mostrar otra temporada.

Si la búsqueda coincide con más de un piloto (por ejemplo "Verstappen", que coincide con Jos y con Max), se listan las coincidencias para que se pueda repetir la búsqueda con un dato más específico (nombre completo, código de 3 letras o driverId).

## Qué muestra el resultado de una carrera

Para cada carrera se listan los pilotos ordenados por posición final, con:

- **Pos.**: posición final
- **Auto**: número de auto
- **Piloto**: nombre completo
- **Escudería**: equipo
- **Salida**: posición de largada
- **Cambio**: variación de posiciones entre la largada y la llegada (▲ subió, ▼ bajó, `=` sin cambios)

## Qué muestra el historial de ganadores de un circuito

Para cada año que se corrió en el circuito se lista, ordenado por temporada:

- **Año**: temporada
- **Gran Premio**: nombre de la carrera
- **Fecha**: fecha de la carrera
- **Ganador**: nombre completo del piloto ganador
- **Escudería**: equipo del ganador
- **Vuelta rápida**: mejor tiempo de vuelta del ganador en esa carrera (la API solo tiene este dato desde 2004 en adelante; en años anteriores se muestra `-`)

## Qué muestra la búsqueda de un piloto

Para cada carrera del piloto se lista, ordenado por temporada y ronda:

- **Año** / **Ronda**: temporada y número de carrera dentro de esa temporada
- **Gran Premio**: nombre de la carrera
- **Fecha**: fecha de la carrera
- **Salida** / **Final**: posición de largada y posición final
- **Escudería**: equipo con el que corrió esa carrera

## Solución de problemas

**`ModuleNotFoundError: No module named 'requests'` (o `pandas`)**

Significa que el entorno virtual activo no tiene las dependencias instaladas, o que la terminal quedó con un entorno activado que ya no existe (por ejemplo, si se borró la carpeta `venv/` o `.venv/` mientras estaba activada). Solución:

```bash
deactivate
source venv/bin/activate
pip install -r requirements.txt
python3 efeuno.py
```

Si el proyecto no tiene todavía una carpeta `venv/`, seguí los pasos de [Instalación](#instalación) para crearla.

## Tests

El proyecto tiene tests unitarios (sin dependencias externas, usan `unittest.mock` para no llamar a la API real):

```bash
source venv/bin/activate
python3 -m unittest discover -s tests
```
