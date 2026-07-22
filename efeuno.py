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


def obtener_json_paginado(path, tabla, clave_lista):
    """Recorre todas las páginas de un endpoint (la API limita a 100 resultados por página)."""
    elementos = []
    offset = 0
    limit = 100
    while True:
        response = requests.get(
            f"{BASE_URL}{path}.json", params={"limit": limit, "offset": offset}, timeout=30
        )
        response.raise_for_status()
        mrdata = response.json().get("MRData", {})
        pagina = mrdata.get(tabla, {}).get(clave_lista, [])
        elementos.extend(pagina)
        total = int(mrdata.get("total", 0))
        offset += len(pagina)
        if not pagina or offset >= total:
            break
    return elementos


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


def buscar_piloto(query):
    """Busca pilotos cuyo nombre, apellido, código o driverId coincidan (parcial, sin mayúsculas) con la consulta.

    Devuelve una lista de dicts: [{driverId, givenName, familyName, code}].
    """
    consulta = query.lower()
    drivers = obtener_json_paginado("/drivers", "DriverTable", "Drivers")

    coincidencias = []
    for d in drivers:
        given_name = d.get("givenName", "")
        family_name = d.get("familyName", "")
        code = d.get("code", "")
        driver_id = d.get("driverId", "")
        campos = [given_name, family_name, code, driver_id, f"{given_name} {family_name}"]
        if any(consulta in campo.lower() for campo in campos if campo):
            coincidencias.append(
                {
                    "driverId": driver_id,
                    "givenName": given_name,
                    "familyName": family_name,
                    "code": code,
                }
            )
    return coincidencias


class SinResultadosPiloto(Exception):
    """El piloto existe pero no tiene resultados para la consulta pedida (p. ej. esa temporada)."""


def obtener_resultados_piloto(driver_id, year=None):
    """Devuelve un DataFrame con los resultados de un piloto (una temporada o todas).

    Columnas: season, round, raceName, date, pos_grid, pos_final, constructor.
    """
    prefijo = f"/{year}" if year else ""
    races = obtener_json_paginado(f"{prefijo}/drivers/{driver_id}/results", "RaceTable", "Races")
    if not races:
        if year:
            raise SinResultadosPiloto(
                f"El piloto no tiene resultados en la temporada {year}. "
                "Probá con otro año o con 'all' para ver toda su carrera."
            )
        raise SinResultadosPiloto("No se encontraron resultados para el piloto")

    filas = []
    for race in races:
        resultado = race.get("Results", [{}])[0]
        constructor = resultado.get("Constructor", {})
        filas.append(
            {
                "season": race.get("season"),
                "round": race.get("round"),
                "raceName": race.get("raceName"),
                "date": race.get("date"),
                "pos_grid": resultado.get("grid"),
                "pos_final": resultado.get("position"),
                "constructor": constructor.get("name"),
            }
        )

    df = pd.DataFrame(filas)
    df["season"] = pd.to_numeric(df["season"], errors="coerce")
    df["round"] = pd.to_numeric(df["round"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["pos_grid"] = pd.to_numeric(df["pos_grid"], errors="coerce")
    df["pos_final"] = pd.to_numeric(df["pos_final"], errors="coerce")
    df.sort_values(["season", "round"], inplace=True)
    return df.reset_index(drop=True)


def mostrar_coincidencias_piloto(pilotos, consulta):
    print(f"Se encontraron varios pilotos que coinciden con '{consulta}':")
    for p in pilotos:
        code = f" ({p['code']})" if p.get("code") else ""
        print(f"  - {p['givenName']} {p['familyName']}{code} [{p['driverId']}]")
    print("\nEspecificá mejor el nombre o apellido para elegir un piloto.")


def mostrar_resultados_piloto(df_resultados, piloto, year):
    titulo_year = "todas las temporadas" if year is None else str(year)
    print(f"Resultados de {piloto['givenName']} {piloto['familyName']} ({titulo_year}):")
    print(f"{'Año':<6}{'Ronda':<7}{'Gran Premio':<28}{'Fecha':<12}{'Salida':<8}{'Final':<7}{'Escudería':<16}")
    for _, row in df_resultados.iterrows():
        fecha = row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else ""
        salida = int(row["pos_grid"]) if pd.notna(row["pos_grid"]) else "-"
        final = int(row["pos_final"]) if pd.notna(row["pos_final"]) else "-"
        gp_name = row["raceName"]
        if len(gp_name) > 28:
            gp_name = gp_name[:25] + "..."
        print(
            f"{int(row['season']):<6}"
            f"{int(row['round']):<7}"
            f"{gp_name:<28}"
            f"{fecha:<12}"
            f"{str(salida):<8}"
            f"{str(final):<7}"
            f"{row['constructor']:<16}"
        )


def parsear_year(year_arg, year_por_defecto):
    if not year_arg:
        return year_por_defecto
    try:
        return int(year_arg)
    except ValueError:
        raise Exception(f"El año '{year_arg}' no es válido")


def main():
    year_actual = pd.Timestamp.now().year
    argumento = sys.argv[1] if len(sys.argv) > 1 else None
    year_arg = sys.argv[2] if len(sys.argv) > 2 else None

    if argumento == "circuitos":
        year = parsear_year(year_arg, year_actual)
        df_temporada = obtener_temporada(year)
        mostrar_circuitos(df_temporada, year)
        return

    if argumento is None:
        df_temporada = obtener_temporada(year_actual)
        now = pd.Timestamp.now(tz="UTC")
        pasadas = df_temporada[df_temporada["date_start"] <= now]
        if pasadas.empty:
            raise Exception(f"Todavía no se corrió ninguna carrera en {year_actual}")
        carrera = pasadas.iloc[-1]
        etiqueta = f"{carrera['meeting_name']} ({carrera['date_start'].strftime('%Y-%m-%d')})"
        mostrar_resultado_carrera(int(carrera["year"]), int(carrera["round"]), etiqueta)
        return

    todas_temporadas = year_arg is not None and year_arg.lower() == "all"
    carrera_encontrada = None
    year_para_circuito = None

    if not todas_temporadas:
        year_para_circuito = parsear_year(year_arg, year_actual)
        try:
            df_temporada = obtener_temporada(year_para_circuito)
            carrera_encontrada = buscar_circuito(df_temporada, argumento)
        except Exception:
            carrera_encontrada = None

    if carrera_encontrada is not None:
        now = pd.Timestamp.now(tz="UTC")
        if carrera_encontrada["date_start"] > now:
            print(
                f"{carrera_encontrada['meeting_name']} todavía no se corrió. "
                f"Fecha programada: {carrera_encontrada['date_start'].strftime('%Y-%m-%d')}"
            )
            return
        etiqueta = (
            f"{carrera_encontrada['meeting_name']} "
            f"({carrera_encontrada['date_start'].strftime('%Y-%m-%d')})"
        )
        mostrar_resultado_carrera(
            int(carrera_encontrada["year"]), int(carrera_encontrada["round"]), etiqueta
        )
        return

    pilotos = buscar_piloto(argumento)
    if not pilotos:
        raise Exception(f"No se encontró ninguna carrera ni ningún piloto que coincida con '{argumento}'")
    if len(pilotos) > 1:
        mostrar_coincidencias_piloto(pilotos, argumento)
        return

    year_piloto = None if todas_temporadas else year_para_circuito
    piloto = pilotos[0]
    try:
        df_resultados = obtener_resultados_piloto(piloto["driverId"], year=year_piloto)
    except SinResultadosPiloto:
        if year_arg is not None:
            raise
        print(
            f"{piloto['givenName']} {piloto['familyName']} no corrió en {year_piloto}. "
            "Mostrando toda su carrera:\n"
        )
        year_piloto = None
        df_resultados = obtener_resultados_piloto(piloto["driverId"], year=None)
    mostrar_resultados_piloto(df_resultados, piloto, year_piloto)


if __name__ == "__main__":
    main()
