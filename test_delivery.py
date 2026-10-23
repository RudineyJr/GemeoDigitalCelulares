import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import core
from collect import handle_payload
from simulate import simulate
from mqtt_transport import ReliablePublisher, archive_events

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patch=patch.object(core,"DB",Path(self.tmp.name)/"test.sqlite3")
        self.patch.start()
        self.conn=core.connect()
        self.events=simulate(5,defect_rate=0)
        self.manifest=core.make_manifest(self.events)

    def tearDown(self):
        self.conn.close()
        self.patch.stop()
        self.tmp.cleanup()

    def batch(self,events=None):
        return dict(tipo="lote",execucao=self.events[0]["execucao"],eventos=self.events if events is None else events)

    def test_batch_commit_and_final_confirmation(self):
        handle_payload(self.conn,self.batch())
        reply=handle_payload(self.conn,self.manifest)
        self.assertEqual(reply["recebidos"],len(self.events))
        self.assertEqual(reply["resumo"]["concluidas"],5)
        reader=core.connect()
        try:
            self.assertEqual(reader.execute("SELECT COUNT(*) FROM eventos").fetchone()[0],len(self.events))
        finally:
            reader.close()

    def test_lost_ack_retry_does_not_duplicate(self):
        handle_payload(self.conn,self.batch())
        handle_payload(self.conn,self.batch())
        reply=handle_payload(self.conn,self.manifest)
        self.assertEqual(reply["recebidos"],len(self.events))

    def test_missing_event_cannot_receive_final_certificate(self):
        core.save_many(self.conn,self.events[:4]+self.events[5:])
        with self.assertRaisesRegex(ValueError,"incompleto"):
            handle_payload(self.conn,self.manifest)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM execucoes WHERE status='validada'").fetchone()[0],0)

    def test_wrong_digest_is_rejected(self):
        handle_payload(self.conn,self.batch())
        broken={**self.manifest,"digest":"errado"}
        with self.assertRaises(ValueError):handle_payload(self.conn,broken)

    def test_wrong_summary_is_rejected(self):
        handle_payload(self.conn,self.batch())
        broken={**self.manifest,"resumo":{**self.manifest["resumo"],"concluidas":999}}
        with self.assertRaises(ValueError):handle_payload(self.conn,broken)

    def test_invalid_batch_is_atomic(self):
        broken=copy.deepcopy(self.events)
        broken[-1]["estacao"]="inexistente"
        with self.assertRaises(ValueError):handle_payload(self.conn,self.batch(broken))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM eventos").fetchone()[0],0)

    def test_no_application_ack_is_failure_even_if_broker_acks(self):
        sender=ReliablePublisher.__new__(ReliablePublisher)
        import threading
        sender.ack=threading.Event()
        sender.reply_topic="celulares/confirmacoes/test"
        sender.timeout=0
        sender.client=Mock()
        sender.client.publish.return_value.is_published.return_value=True
        with self.assertRaises(TimeoutError):sender.request(self.batch())
        self.assertEqual(sender.client.publish.call_count,3)

    def test_archive_has_all_generated_events_and_manifest(self):
        with patch("mqtt_transport.ARCHIVES",Path(self.tmp.name)/"transmissoes"):
            path=archive_events(self.events)
            events=[json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            manifest=json.loads(path.with_suffix(".manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(events,self.events)
            self.assertEqual(manifest,self.manifest)

if __name__=="__main__":unittest.main()
