import unittest
from core import PROCESS, make_manifest, save_many, confirm_run
from simulate import simulate
from station_config import resolve_times
import core
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


class StationConfigTests(unittest.TestCase):
    def test_invalid_times(self):
        for value in (0, -1, float("nan"), float("inf"), True, "19", None):
            with self.assertRaises(ValueError):
                simulate(1, station_times={"Bateria": value})
        for config in ({"Inexistente": 5}, {"Forno de refusão": 19}, []):
            with self.assertRaises(ValueError):
                resolve_times(config)

    def test_custom_times_take_priority_and_do_not_change_original(self):
        events = simulate(1, defect_rate=0, lean_full=True, station_times={"Bateria": 17.5}, scenario_name="Ensaio A")
        config = events[0]["detalhes"]["configuracao"]
        self.assertEqual(config["cenario"], "Ensaio A")
        trace = [e for e in events if e["estacao"] == "Bateria"]
        self.assertEqual(trace[-1]["tempo_simulado"]-trace[1]["tempo_simulado"], 17.5)
        self.assertEqual(dict(PROCESS)["Bateria"], 27)
        self.assertEqual(config["tempos"]["Câmera traseira"], 19)

    def test_custom_execution_persists_its_configuration(self):
        events = simulate(3, defect_rate=0, station_times={"Bateria": 18}, scenario_name="Meu cenário")
        with TemporaryDirectory() as folder, patch.object(core, "DB", Path(folder)/"teste.sqlite3"):
            conn = core.connect()
            try:
                save_many(conn, events)
                confirm_run(conn, make_manifest(events), "direto")
                import json
                config = json.loads(conn.execute("SELECT detalhes FROM eventos WHERE sequencia=0").fetchone()[0])["configuracao"]
                self.assertEqual(config["tempos"]["Bateria"], 18)
                self.assertEqual(config["cenario"], "Meu cenário")
            finally:
                conn.close()
