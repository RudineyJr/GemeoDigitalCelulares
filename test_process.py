import unittest
from simulate import simulate
from core import save, STATIONS, PROCESS, CAPACITIES
import sqlite3

class ProcessTests(unittest.TestCase):
    def test_all_good_reach_packaging(self):
        events = simulate(10, defect_rate=0)
        final = [e for e in events if e["estacao"] == "Embalagem" and e["evento"] == "saida"]
        self.assertEqual(len(final), 10)
        for piece in {e["id_peca"] for e in events}:
            trace = [e for e in events if e["id_peca"] == piece]
            self.assertEqual([e["estacao"] for e in trace if e["evento"] == "saida"], STATIONS)
            self.assertEqual([e["tempo_simulado"] for e in trace], sorted(e["tempo_simulado"] for e in trace))

    def test_rejected_never_packaged(self):
        events = simulate(10, defect_rate=1)
        self.assertEqual(sum(e["resultado"] == "reprovada" for e in events), 10)
        self.assertFalse(any(e["estacao"] == "Embalagem" for e in events))

    def test_database_deduplicates_delivery(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE eventos (id_evento TEXT PRIMARY KEY, execucao TEXT, id_peca TEXT, estacao TEXT, tempo_simulado REAL, evento TEXT, resultado TEXT, detalhes TEXT)")
        event = simulate(1)[0]
        save(conn, event)
        save(conn, event)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM eventos").fetchone()[0], 1)
        conn.close()

    def test_one_piece_nominal_duration(self):
        events = simulate(1, defect_rate=0)
        self.assertEqual(events[-1]["tempo_simulado"], sum(duration for _, duration in PROCESS))
        self.assertEqual(len(events), len(STATIONS) * 3)

    def test_rejected_visits_all_stations_until_test(self):
        events = simulate(1, defect_rate=1, spi_enabled=False, aoi_enabled=False)
        self.assertEqual([e["estacao"] for e in events if e["evento"] == "saida"], [s for s in STATIONS[:-1] if s not in ("SPI", "AOI")])

    def test_shift_stops_without_draining_line(self):
        events = simulate(shift_hours=8, defect_rate=0)
        self.assertEqual(len({e["id_peca"] for e in events}), 1440)
        self.assertTrue(all(e["tempo_simulado"] < 28800 for e in events))
        finished = sum(e["estacao"] == "Embalagem" and e["evento"] == "saida" for e in events)
        self.assertLess(finished, 1440)
        self.assertEqual(events[0]["detalhes"]["configuracao"]["turno_segundos"], 28800)

    def test_invalid_shift_duration(self):
        for hours in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                simulate(shift_hours=hours)

    def test_station_capacity(self):
        events = simulate(30, defect_rate=0)
        occupied = {name: set() for name in STATIONS}
        oven_max = 0
        oven_entries = []
        for e in events:
            station = e["estacao"]
            if e["evento"] == "entrada":
                occupied[station].add(e["id_peca"])
                self.assertLessEqual(len(occupied[station]), CAPACITIES[station])
                if station == "Forno de refusão":
                    oven_max = max(oven_max, len(occupied[station]))
                    oven_entries.append(e["tempo_simulado"])
            elif e["evento"] == "saida":
                occupied[station].remove(e["id_peca"])
        self.assertTrue(all(not plates for plates in occupied.values()))
        self.assertGreater(oven_max, 1)
        self.assertTrue(all(b-a >= 20 for a,b in zip(oven_entries, oven_entries[1:])))

    def test_spi_catches_paste_before_components(self):
        events = simulate(5, defect_rate=1, placement_rate=0, reflow_rate=0, spi_detection=1)
        failures = [e for e in events if e["resultado"] == "reprovada"]
        self.assertEqual(len(failures), 5)
        self.assertTrue(all(e["estacao"] == "SPI" for e in failures))
        self.assertFalse(any(e["estacao"].startswith("Pick") for e in events))

    def test_aoi_catches_new_defects_after_spi(self):
        events = simulate(5, defect_rate=0, placement_rate=1, reflow_rate=0, aoi_detection=1)
        failures = [e for e in events if e["resultado"] == "reprovada"]
        self.assertEqual(len(failures), 5)
        self.assertTrue(all(e["estacao"] == "AOI" for e in failures))
        self.assertFalse(any(e["estacao"] == "Gravação de FW" for e in events))

    def test_missed_defects_reach_final_test(self):
        events = simulate(5, defect_rate=1, spi_detection=0, aoi_detection=0)
        failures = [e for e in events if e["resultado"] == "reprovada"]
        self.assertEqual(len(failures), 5)
        self.assertTrue(all(e["estacao"] == "Teste funcional" for e in failures))

    def test_reflow_defect_is_detected_by_aoi(self):
        events = simulate(5, defect_rate=0, placement_rate=0, reflow_rate=1, aoi_detection=1)
        failures = [e for e in events if e["resultado"] == "reprovada"]
        self.assertEqual(len(failures), 5)
        self.assertTrue(all(e["estacao"] == "AOI" for e in failures))


if __name__ == "__main__":
    unittest.main()
