import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import efeuno


def _mock_response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


class BuscarPilotoTests(unittest.TestCase):
    DRIVERS_PAGE = {
        "MRData": {
            "total": "3",
            "DriverTable": {
                "Drivers": [
                    {
                        "driverId": "alonso",
                        "code": "ALO",
                        "givenName": "Fernando",
                        "familyName": "Alonso",
                    },
                    {
                        "driverId": "verstappen",
                        "code": "",
                        "givenName": "Jos",
                        "familyName": "Verstappen",
                    },
                    {
                        "driverId": "max_verstappen",
                        "code": "VER",
                        "givenName": "Max",
                        "familyName": "Verstappen",
                    },
                ]
            },
        }
    }

    @patch("efeuno.requests.get")
    def test_mapea_nombre_a_driver_id_unico(self, mock_get):
        mock_get.return_value = _mock_response(self.DRIVERS_PAGE)

        resultado = efeuno.buscar_piloto("alonso")

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["driverId"], "alonso")
        self.assertEqual(resultado[0]["familyName"], "Alonso")

    @patch("efeuno.requests.get")
    def test_busqueda_case_insensitive_y_parcial(self, mock_get):
        mock_get.return_value = _mock_response(self.DRIVERS_PAGE)

        resultado = efeuno.buscar_piloto("ALON")

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]["driverId"], "alonso")

    @patch("efeuno.requests.get")
    def test_apellido_ambiguo_devuelve_todas_las_coincidencias(self, mock_get):
        mock_get.return_value = _mock_response(self.DRIVERS_PAGE)

        resultado = efeuno.buscar_piloto("verstappen")

        driver_ids = {p["driverId"] for p in resultado}
        self.assertEqual(driver_ids, {"verstappen", "max_verstappen"})

    @patch("efeuno.requests.get")
    def test_sin_coincidencias_devuelve_lista_vacia(self, mock_get):
        mock_get.return_value = _mock_response(self.DRIVERS_PAGE)

        resultado = efeuno.buscar_piloto("piloto_inexistente_xyz")

        self.assertEqual(resultado, [])

    @patch("efeuno.requests.get")
    def test_pagina_resultados_de_drivers(self, mock_get):
        pagina_1 = {
            "MRData": {
                "total": "2",
                "DriverTable": {
                    "Drivers": [self.DRIVERS_PAGE["MRData"]["DriverTable"]["Drivers"][0]]
                },
            }
        }
        pagina_2 = {
            "MRData": {
                "total": "2",
                "DriverTable": {
                    "Drivers": [self.DRIVERS_PAGE["MRData"]["DriverTable"]["Drivers"][1]]
                },
            }
        }
        mock_get.side_effect = [_mock_response(pagina_1), _mock_response(pagina_2)]

        resultado = efeuno.buscar_piloto("a")

        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(len(resultado), 2)


class ObtenerResultadosPilotoTests(unittest.TestCase):
    RESULTS_PAYLOAD = {
        "MRData": {
            "total": "2",
            "RaceTable": {
                "Races": [
                    {
                        "season": "2012",
                        "round": "1",
                        "raceName": "Australian Grand Prix",
                        "date": "2012-03-18",
                        "Results": [
                            {
                                "grid": "12",
                                "position": "5",
                                "Constructor": {"name": "Ferrari"},
                            }
                        ],
                    },
                    {
                        "season": "2012",
                        "round": "2",
                        "raceName": "Malaysian Grand Prix",
                        "date": "2012-03-25",
                        "Results": [
                            {
                                "grid": "8",
                                "position": "1",
                                "Constructor": {"name": "Ferrari"},
                            }
                        ],
                    },
                ]
            },
        }
    }

    @patch("efeuno.requests.get")
    def test_normaliza_columnas_y_tipos(self, mock_get):
        mock_get.return_value = _mock_response(self.RESULTS_PAYLOAD)

        df = efeuno.obtener_resultados_piloto("alonso", year=2012)

        self.assertListEqual(
            list(df.columns),
            ["season", "round", "raceName", "date", "pos_grid", "pos_final", "constructor"],
        )
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["season"], 2012)
        self.assertEqual(df.iloc[0]["round"], 1)
        self.assertEqual(df.iloc[0]["pos_grid"], 12)
        self.assertEqual(df.iloc[0]["pos_final"], 5)
        self.assertEqual(df.iloc[0]["constructor"], "Ferrari")
        self.assertTrue(str(df.iloc[0]["date"].date()) == "2012-03-18")

    @patch("efeuno.requests.get")
    def test_ordena_por_temporada_y_ronda(self, mock_get):
        payload_desordenado = {
            "MRData": {
                "total": "2",
                "RaceTable": {
                    "Races": [
                        self.RESULTS_PAYLOAD["MRData"]["RaceTable"]["Races"][1],
                        self.RESULTS_PAYLOAD["MRData"]["RaceTable"]["Races"][0],
                    ]
                },
            }
        }
        mock_get.return_value = _mock_response(payload_desordenado)

        df = efeuno.obtener_resultados_piloto("alonso", year=2012)

        self.assertEqual(list(df["round"]), [1, 2])

    @patch("efeuno.requests.get")
    def test_sin_resultados_en_una_temporada_lanza_sin_resultados_piloto(self, mock_get):
        mock_get.return_value = _mock_response(
            {"MRData": {"total": "0", "RaceTable": {"Races": []}}}
        )

        with self.assertRaises(efeuno.SinResultadosPiloto):
            efeuno.obtener_resultados_piloto("fangio", year=2026)

    @patch("efeuno.requests.get")
    def test_sin_resultados_en_ninguna_temporada_lanza_sin_resultados_piloto(self, mock_get):
        mock_get.return_value = _mock_response(
            {"MRData": {"total": "0", "RaceTable": {"Races": []}}}
        )

        with self.assertRaises(efeuno.SinResultadosPiloto):
            efeuno.obtener_resultados_piloto("piloto_sin_datos", year=None)

    @patch("efeuno.requests.get")
    def test_year_none_consulta_endpoint_de_todas_las_temporadas(self, mock_get):
        mock_get.return_value = _mock_response(self.RESULTS_PAYLOAD)

        efeuno.obtener_resultados_piloto("alonso", year=None)

        url_llamada = mock_get.call_args[0][0]
        self.assertIn("/drivers/alonso/results.json", url_llamada)
        self.assertNotRegex(url_llamada, r"/\d{4}/drivers")


class MainFallbackPilotoTests(unittest.TestCase):
    FANGIO = {"driverId": "fangio", "givenName": "Juan", "familyName": "Fangio", "code": ""}

    def _df_resultados_ok(self):
        return pd.DataFrame(
            {
                "season": [1950],
                "round": [1],
                "raceName": ["British Grand Prix"],
                "date": [pd.Timestamp("1950-05-13")],
                "pos_grid": [3],
                "pos_final": [12],
                "constructor": ["Alfa Romeo"],
            }
        )

    @patch("efeuno.obtener_resultados_piloto")
    @patch("efeuno.buscar_piloto")
    @patch("efeuno.obtener_temporada")
    @patch("sys.argv", ["efeuno.py", "fangio"])
    def test_sin_year_cae_a_toda_la_carrera_si_no_corrio_en_el_actual(
        self, mock_temporada, mock_buscar_piloto, mock_resultados
    ):
        mock_temporada.side_effect = Exception("no hay calendario (irrelevante para este test)")
        mock_buscar_piloto.return_value = [self.FANGIO]
        mock_resultados.side_effect = [
            efeuno.SinResultadosPiloto("sin resultados en la temporada actual"),
            self._df_resultados_ok(),
        ]

        efeuno.main()

        self.assertEqual(mock_resultados.call_count, 2)
        self.assertIsNotNone(mock_resultados.call_args_list[0].kwargs["year"])
        self.assertIsNone(mock_resultados.call_args_list[1].kwargs["year"])

    @patch("efeuno.obtener_resultados_piloto")
    @patch("efeuno.buscar_piloto")
    @patch("efeuno.obtener_temporada")
    @patch("sys.argv", ["efeuno.py", "fangio", "1900"])
    def test_con_year_explicito_no_hace_fallback_automatico(
        self, mock_temporada, mock_buscar_piloto, mock_resultados
    ):
        mock_temporada.side_effect = Exception("no hay calendario (irrelevante para este test)")
        mock_buscar_piloto.return_value = [self.FANGIO]
        mock_resultados.side_effect = efeuno.SinResultadosPiloto("sin resultados en 1900")

        with self.assertRaises(efeuno.SinResultadosPiloto):
            efeuno.main()

        self.assertEqual(mock_resultados.call_count, 1)


if __name__ == "__main__":
    unittest.main()
