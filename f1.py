import sys
import requests
import pandas as pd

BASE_URL = "https://api.openf1.org/v1"


def obtener_temporada(year):
    """Devuelve un DataFrame con las carreras (no sprints, no testing) del año dado."""
    sesiones = requests.get(f"{BASE_URL}/sessions?year={year}&session_type=Race").json()
    df_sesiones = pd.DataFrame(sesiones)
    df_sesiones = df_sesiones[df_sesiones['session_name'] == 'Race']
    if df_sesiones.empty:
        raise Exception(f"No se encontraron carreras para el año {year}")

    reuniones = requests.get(f"{BASE_URL}/meetings?year={year}").json()
    df_reuniones = pd.DataFrame(reuniones)[
        ['meeting_key', 'meeting_name', 'circuit_short_name', 'location', 'country_name']
    ]

    df_temporada = df_sesiones[['meeting_key', 'session_key', 'date_start']].merge(
        df_reuniones, on='meeting_key', how='left'
    )
    df_temporada['date_start'] = pd.to_datetime(df_temporada['date_start'], utc=True)
    df_temporada.sort_values('date_start', inplace=True)
    return df_temporada.reset_index(drop=True)


def mostrar_circuitos(df_temporada, year):
    now = pd.Timestamp.now(tz='UTC')
    print(f"Calendario {year}:")
    print(f"{'Fecha':<12}{'Gran Premio':<28}{'Circuito':<20}{'Corrida':<8}")
    for _, row in df_temporada.iterrows():
        corrida = "✓" if row['date_start'] <= now else ""
        print(
            f"{row['date_start'].strftime('%Y-%m-%d'):<12}"
            f"{row['meeting_name']:<28}"
            f"{row['circuit_short_name']:<20}"
            f"{corrida:<8}"
        )


def buscar_circuito(df_temporada, consulta):
    consulta = consulta.lower()
    campos = ['meeting_name', 'circuit_short_name', 'location', 'country_name']
    mask = df_temporada[campos].apply(
        lambda col: col.str.lower().str.contains(consulta, na=False)
    ).any(axis=1)
    coincidencias = df_temporada[mask]
    if coincidencias.empty:
        raise Exception(f"No se encontró ninguna carrera que coincida con '{consulta}'")
    return coincidencias.iloc[0]


def mostrar_resultado_carrera(session_key, etiqueta):
    # Paso 1: Obtener las posiciones de los pilotos
    positions_data = requests.get(f"{BASE_URL}/position?session_key={session_key}").json()
    df_positions = pd.DataFrame(positions_data)
    if df_positions.empty:
        raise Exception("No se encontraron posiciones para la sesión")

    # Paso 2: Obtener los datos de los pilotos (nombre, escudería, número)
    drivers_data = requests.get(f"{BASE_URL}/drivers?session_key={session_key}").json()
    df_drivers = pd.DataFrame(drivers_data)[['driver_number', 'full_name', 'team_name']].drop_duplicates()

    # Paso 3: Procesar posición de largada (primer registro) y posición final (último registro)
    df_positions['date'] = pd.to_datetime(df_positions['date'])
    df_positions.sort_values(['driver_number', 'date'], inplace=True)

    df_largada = df_positions.groupby('driver_number').first().reset_index()[['driver_number', 'position']]
    df_largada.rename(columns={'position': 'pos_largada'}, inplace=True)

    df_llegada = df_positions.groupby('driver_number').last().reset_index()[['driver_number', 'position']]
    df_llegada.rename(columns={'position': 'pos_final'}, inplace=True)

    # Unir todo
    df_resultado = df_llegada.merge(df_largada, on='driver_number').merge(df_drivers, on='driver_number', how='left')
    df_resultado.sort_values('pos_final', inplace=True)

    def indicador(row):
        diff = row['pos_largada'] - row['pos_final']
        if diff > 0:
            return f"▲ {diff}"
        elif diff < 0:
            return f"▼ {abs(diff)}"
        return "="

    df_resultado['cambio'] = df_resultado.apply(indicador, axis=1)

    # Mostrar resultados en formato de tabla legible
    print(f"Resultado de: {etiqueta}")
    print(f"{'Pos.':<5}{'Auto':<6}{'Piloto':<22}{'Escudería':<16}{'Salida':<8}{'Cambio':<8}")
    for _, row in df_resultado.iterrows():
        print(
            f"{int(row['pos_final']):<5}"
            f"{int(row['driver_number']):<6}"
            f"{row['full_name']:<22}"
            f"{row['team_name']:<16}"
            f"{int(row['pos_largada']):<8}"
            f"{row['cambio']:<8}"
        )


def main():
    year = pd.Timestamp.now().year
    argumento = sys.argv[1] if len(sys.argv) > 1 else None

    if argumento == 'circuitos':
        df_temporada = obtener_temporada(year)
        mostrar_circuitos(df_temporada, year)
        return

    df_temporada = obtener_temporada(year)
    now = pd.Timestamp.now(tz='UTC')

    if argumento is None:
        pasadas = df_temporada[df_temporada['date_start'] <= now]
        if pasadas.empty:
            raise Exception(f"Todavía no se corrió ninguna carrera en {year}")
        carrera = pasadas.iloc[-1]
        etiqueta = f"{carrera['meeting_name']} ({carrera['date_start'].strftime('%Y-%m-%d')})"
        mostrar_resultado_carrera(carrera['session_key'], etiqueta)
    else:
        carrera = buscar_circuito(df_temporada, argumento)
        if carrera['date_start'] > now:
            print(
                f"{carrera['meeting_name']} todavía no se corrió. "
                f"Fecha programada: {carrera['date_start'].strftime('%Y-%m-%d')}"
            )
            return
        etiqueta = f"{carrera['meeting_name']} ({carrera['date_start'].strftime('%Y-%m-%d')})"
        mostrar_resultado_carrera(carrera['session_key'], etiqueta)


if __name__ == '__main__':
    main()
