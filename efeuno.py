import sys
import requests
import pandas as pd

BASE_URL = "https://api.jolpi.ca/ergast/f1"


def obtener_json(path):
    response = requests.get(f"{BASE_URL}{path}.json", timeout=30)
    response.raise_for_status()
    payload = response.json()
    mrdata = payload.get("MRData", {})
    table = mrdata.get("RaceTable", {})
    return mrdata, table


def obtener_temporada(year):
    """Devuelve un DataFrame con las carreras del año dado usando Jolpica-F1."""
    _, table = obtener_json(f"/{year}/races")
    carreras = table.get("Races", [])
    if not carreras:
        raise Exception(f"No se encontraron carreras para el año {year}")

    df = pd.DataFrame(carreras)
    df = df.copy()
    df["meeting_name"] = df["raceName"]
    df["circuit_id"] = df["Circuit"].apply(
        lambda value: value.get("circuitId", "") if isinstance(value, dict) else ""
    )
    df["circuit_short_name"] = df["circuit_id"].apply(
        lambda cid: cid.replace("_", " ").title() if isinstance(cid, str) and cid else ""
    )
    df["location"] = df["Circuit"].apply(
        lambda value: value.get("Location", {}).get("locality", "") if isinstance(value, dict) else ""
    )
    df["country_name"] = df["Circuit"].apply(
        lambda value: value.get("Location", {}).get("country", "") if isinstance(value, dict) else ""
    )
    df["date_start"] = pd.to_datetime(df["date"], utc=True)
    df["year"] = pd.to_numeric(df["season"], errors="coerce")
    df["round"] = pd.to_numeric(df["round"], errors="coerce")

    columnas = [
        "year",
        "round",
        "meeting_name",
        "circuit_short_name",
        "location",
        "country_name",
        "date_start",
        "url",
    ]
    df_temporada = df[columnas].copy()
    df_temporada.sort_values("date_start", inplace=True)
    return df_temporada.reset_index(drop=True)


def mostrar_circuitos(df_temporada, year):
    now = pd.Timestamp.now(tz="UTC")
    print(f"Calendario {year}:")
    print(f"{'Fecha':<12}{'Gran Premio':<28}{'Circuito':<20}{'Corrida':<8}")
    for _, row in df_temporada.iterrows():
        corrida = "✓" if row["date_start"] <= now else ""
        circuit_name = row['circuit_short_name']
        if len(circuit_name) > 20:
            circuit_name = circuit_name[:17] + '...'
        print(
            f"{row['date_start'].strftime('%Y-%m-%d'):<12}"
            f"{row['meeting_name']:<28}"
            f"{circuit_name:<20}"
            f"{corrida:<8}"
        )
    print("\nPara buscar una carrera, usa uno de los valores de la columna Circuito o del Gran Premio.")


def buscar_circuito(df_temporada, consulta):
    consulta = consulta.lower()
    campos = ["meeting_name", "circuit_short_name", "location", "country_name"]
    mask = df_temporada[campos].apply(
        lambda col: col.str.lower().str.contains(consulta, na=False)
    ).any(axis=1)
    coincidencias = df_temporada[mask]
    if coincidencias.empty:
        raise Exception(f"No se encontró ninguna carrera que coincida con '{consulta}'")
    return coincidencias.iloc[0]


def mostrar_resultado_carrera(year, round_number, etiqueta):
    _, table = obtener_json(f"/{year}/{round_number}/results")
    races = table.get("Races", [])
    if not races:
        raise Exception("No se encontraron resultados para la carrera")

    race = races[0]
    results = race.get("Results", [])
    if not results:
        raise Exception("No se encontraron resultados para la carrera")

    df_results = pd.DataFrame(results)
    if df_results.empty:
        raise Exception("No se encontraron resultados para la carrera")

    driver_data = pd.json_normalize(df_results["Driver"])
    constructor_data = pd.json_normalize(df_results["Constructor"])

    df_results = df_results.copy()
    df_results["driver_number"] = pd.to_numeric(df_results["number"], errors="coerce")
    df_results["full_name"] = driver_data["givenName"] + " " + driver_data["familyName"]
    df_results["team_name"] = constructor_data["name"]
    df_results["pos_largada"] = pd.to_numeric(df_results["grid"], errors="coerce")
    df_results["pos_final"] = pd.to_numeric(df_results["position"], errors="coerce")

    df_results = df_results[["driver_number", "full_name", "team_name", "pos_largada", "pos_final"]].copy()
    df_results = df_results.dropna(subset=["pos_largada", "pos_final"])
    df_results = df_results.sort_values("pos_final")

    def indicador(row):
        diff = row["pos_largada"] - row["pos_final"]
        if diff > 0:
            return f"▲ {int(diff)}"
        elif diff < 0:
            return f"▼ {int(abs(diff))}"
        return "="

    df_results["cambio"] = df_results.apply(indicador, axis=1)

    print(f"Resultado de: {etiqueta}")
    print(f"{'Pos.':<5}{'Auto':<6}{'Piloto':<22}{'Escudería':<16}{'Salida':<8}{'Cambio':<8}")
    for _, row in df_results.iterrows():
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
    year_arg = sys.argv[2] if len(sys.argv) > 2 else None

    if year_arg:
        try:
            year = int(year_arg)
        except ValueError:
            raise Exception(f"El año '{year_arg}' no es válido")

    if argumento == "circuitos":
        df_temporada = obtener_temporada(year)
        mostrar_circuitos(df_temporada, year)
        return

    df_temporada = obtener_temporada(year)
    now = pd.Timestamp.now(tz="UTC")

    if argumento is None:
        pasadas = df_temporada[df_temporada["date_start"] <= now]
        if pasadas.empty:
            raise Exception(f"Todavía no se corrió ninguna carrera en {year}")
        carrera = pasadas.iloc[-1]
        etiqueta = f"{carrera['meeting_name']} ({carrera['date_start'].strftime('%Y-%m-%d')})"
        mostrar_resultado_carrera(int(carrera["year"]), int(carrera["round"]), etiqueta)
    else:
        carrera = buscar_circuito(df_temporada, argumento)
        if carrera["date_start"] > now:
            print(
                f"{carrera['meeting_name']} todavía no se corrió. "
                f"Fecha programada: {carrera['date_start'].strftime('%Y-%m-%d')}"
            )
            return
        etiqueta = f"{carrera['meeting_name']} ({carrera['date_start'].strftime('%Y-%m-%d')})"
        mostrar_resultado_carrera(int(carrera["year"]), int(carrera["round"]), etiqueta)


if __name__ == "__main__":
    main()
