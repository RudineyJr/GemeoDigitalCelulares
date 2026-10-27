"""Assinante didático, sem gravar no banco principal. Pare com Ctrl+C."""
import paho.mqtt.client as mqtt

TOPICO = "celulares/tutorial/eventos"


def conectado(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"Falha de conexão: {reason_code}")
        return
    client.subscribe(TOPICO, qos=1)


def inscrito(client, userdata, mid, reason_codes, properties):
    print("Pronto para receber no tópico", TOPICO, flush=True)


def recebeu(client, userdata, mensagem):
    print(mensagem.payload.decode("utf-8"), flush=True)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = conectado
client.on_subscribe = inscrito
client.on_message = recebeu
client.connect("127.0.0.1", 1883)
try:
    client.loop_forever()
except KeyboardInterrupt:
    pass
finally:
    client.disconnect()
