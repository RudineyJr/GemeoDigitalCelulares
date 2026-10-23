"""MQTT com confirmação de aplicação após COMMIT, lotes e cópia local para reenvio."""
import json
import threading
import uuid
from pathlib import Path
import paho.mqtt.client as mqtt
from core import make_manifest

ARCHIVES = Path(__file__).with_name("transmissoes")

def archive_events(events):
    ARCHIVES.mkdir(exist_ok=True)
    path = ARCHIVES / (events[0]["execucao"] + ".jsonl")
    with path.open("x",encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event,ensure_ascii=False)+"\n")
    path.with_suffix(".manifest.json").write_text(json.dumps(make_manifest(events),ensure_ascii=False,indent=2),encoding="utf-8")
    return path

class ReliablePublisher:
    def __init__(self, host="localhost", archive=True, batch_size=200, timeout=30):
        self.batch_size = batch_size
        self.timeout = timeout
        self.buffer = []
        self.archive = archive
        self.handle = None
        self.path = None
        self.ready = threading.Event()
        self.ack = threading.Event()
        self.reply = None
        self.pending = None
        self.reply_topic = "celulares/confirmacoes/" + uuid.uuid4().hex
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_subscribe = lambda *args: self.ready.set()
        self.client.on_message = self.on_message
        self.client.connect(host,1883,60)
        self.client.loop_start()
        if not self.ready.wait(15):
            self.close()
            raise TimeoutError("Não foi possível assinar confirmações MQTT")

    def on_connect(self,client,userdata,flags,reason,properties):
        if not reason.is_failure:
            client.subscribe(self.reply_topic,qos=1)

    def on_message(self,client,userdata,message):
        try:
            reply=json.loads(message.payload)
            if reply.get("lote_id")==self.pending:
                self.reply=reply
                self.ack.set()
        except (ValueError,TypeError):
            pass

    def request(self, payload):
        self.pending=uuid.uuid4().hex
        payload={**payload,"lote_id":self.pending,"topico_resposta":self.reply_topic}
        self.reply=None
        self.ack.clear()
        for attempt in range(3):
            info=self.client.publish("celulares/eventos",json.dumps(payload,ensure_ascii=False),qos=1)
            info.wait_for_publish(timeout=10)
            if not info.is_published():
                continue
            if self.ack.wait(self.timeout):
                if not self.reply.get("ok"):
                    raise RuntimeError("Coletor rejeitou a gravação: "+self.reply.get("erro","erro desconhecido"))
                return self.reply
        raise TimeoutError("Sem confirmação de gravação no banco. Verifique o coletor. O arquivo local permite reenvio.")

    def emit(self,event):
        if self.archive:
            if self.handle is None:
                ARCHIVES.mkdir(exist_ok=True)
                self.path=ARCHIVES/(event["execucao"]+".jsonl")
                self.handle=self.path.open("x",encoding="utf-8")
            self.handle.write(json.dumps(event,ensure_ascii=False)+"\n")
        self.buffer.append(event)
        if len(self.buffer)>=self.batch_size:
            self.flush()

    def flush(self):
        if self.handle:
            self.handle.flush()
        if self.buffer:
            self.request(dict(tipo="lote",execucao=self.buffer[0]["execucao"],eventos=self.buffer))
            self.buffer=[]

    def finish(self,manifest):
        if self.path:
            self.path.with_suffix(".manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        self.flush()
        reply=self.request(manifest)
        if reply.get("recebidos") != manifest["esperados"] or reply.get("resumo") != manifest["resumo"]:
            raise RuntimeError("Confirmação final diverge dos dados gerados")
        return reply

    def close(self):
        if self.handle:
            self.handle.close()
        self.client.disconnect()
        self.client.loop_stop()


def replay_archive(path,host="localhost"):
    path=Path(path)
    with path.open(encoding="utf-8") as handle:
        events=[json.loads(line) for line in handle if line.strip()]
    if not events or any(e.get("sequencia")!=i or e["execucao"]!=events[0]["execucao"] for i,e in enumerate(events)):
        raise ValueError("Arquivo vazio, com lacunas ou com execuções misturadas")
    manifest_path=path.with_suffix(".manifest.json")
    if not manifest_path.exists():
        raise ValueError("Arquivo sem manifesto de término; a simulação original pode não ter terminado")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    if make_manifest(events)!=manifest:
        raise ValueError("O arquivo não corresponde ao manifesto")
    publisher=ReliablePublisher(host,archive=False)
    try:
        for event in events:publisher.emit(event)
        publisher.finish(manifest)
        print(f"Reenvio confirmado: {manifest['execucao']}, {len(events)} eventos; {manifest['resumo']}")
    finally:
        publisher.close()
