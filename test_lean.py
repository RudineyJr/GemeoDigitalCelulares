import unittest
from simulate import simulate
from lean_analysis import summarize_flow, final_queues, LEAN_FULL_TIMES


class LeanTests(unittest.TestCase):
    def test_full_balance_has_no_backlog_and_preserves_inspection_results(self):
        events = simulate(shift_hours=8, lean_full=True)
        config = events[0]["detalhes"]["configuracao"]
        self.assertEqual(final_queues(events), {})
        self.assertEqual(config["ciclo_ideal_teste_funcional"], 19)
        self.assertEqual(config["cenario"], "SPI/AOI + Lean ampliado")
        local = simulate(shift_hours=8, lean=True)
        def inspections(trace):
            return [(e["id_peca"], e["estacao"], e["resultado"]) for e in trace if e["estacao"] in ("SPI", "AOI") and e["evento"] == "saida"]
        self.assertEqual(inspections(events), inspections(local))
        first = [e for e in events if e["id_peca"] == "P0001"]
        for name, duration in LEAN_FULL_TIMES.items():
            trace = [e for e in first if e["estacao"] == name]
            self.assertEqual(trace[2]["tempo_simulado"] - trace[1]["tempo_simulado"], duration)

    def test_lean_changes_actual_durations_without_mutating_baseline(self):
        lean = simulate(1, defect_rate=0, lean=True)
        baseline = simulate(1, defect_rate=0)
        for name, expected in [("Bateria", 19), ("Alto-falante", 19), ("Microfone", 19), ("Teste funcional", 26)]:
            trace = [e for e in lean if e["estacao"] == name]
            self.assertEqual(trace[2]["tempo_simulado"]-trace[1]["tempo_simulado"], expected)
        self.assertEqual(baseline[0]["detalhes"]["configuracao"]["tempos"]["Bateria"], 27)

    def test_balance_reduces_battery_backlog_and_keeps_defect_draws(self):
        normal = simulate(shift_hours=1)
        lean = simulate(shift_hours=1, lean=True)
        a, b = summarize_flow(normal, 3600), summarize_flow(lean, 3600)
        self.assertGreater(a["fila_bateria_final"], 0)
        self.assertEqual(b["fila_bateria_final"], 0)
        def rejected_at_inspections(events):
            return [(e["id_peca"], e["estacao"]) for e in events if e["resultado"] == "reprovada" and e["estacao"] in ("SPI", "AOI")]
        self.assertEqual(rejected_at_inspections(normal), rejected_at_inspections(lean))

    def test_queue_area_includes_unfinished_wait(self):
        events = [dict(id_peca="P1", estacao="Bateria", tempo_simulado=0, evento="fila", resultado="pendente"), dict(id_peca="P1", estacao="Bateria", tempo_simulado=5, evento="entrada", resultado="pendente"), dict(id_peca="P2", estacao="Bateria", tempo_simulado=10, evento="fila", resultado="pendente")]
        stats = summarize_flow(events, 20)
        self.assertEqual(stats["fila_bateria_final"], 1)
        self.assertEqual(stats["fila_bateria_media"], 0.75)
        self.assertEqual(stats["espera_bateria_media_s"], 5)
