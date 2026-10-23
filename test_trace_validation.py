import unittest
from simulate import simulate
from core import STATIONS
from trace_validation import validate_trace

class TraceValidationTests(unittest.TestCase):
    def convert(self, events):
        return [dict(p=e["id_peca"],s=e["estacao"],e=e["evento"],r=e["resultado"]) for e in events]

    def test_complete_trace(self):
        self.assertEqual(validate_trace(self.convert(simulate(10)), STATIONS), 0)

    def test_unfinished_shift_is_valid(self):
        self.assertEqual(validate_trace(self.convert(simulate(shift_hours=0.1)), STATIONS), 0)

    def test_trace_without_aoi_is_valid(self):
        stations = [name for name in STATIONS if name != "AOI"]
        events = simulate(10, aoi_enabled=False)
        self.assertEqual(validate_trace(self.convert(events), stations), 0)

    def test_missing_event_is_detected(self):
        events=self.convert(simulate(1,defect_rate=0))
        del events[1]
        self.assertGreater(validate_trace(events, STATIONS), 0)
