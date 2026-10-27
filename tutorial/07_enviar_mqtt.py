"""Publica um evento de exemplo num tópico separado do projeto."""
import json
import paho.mqtt.client as mqtt

evento = {"placa": "P1", "estacao": "SPI", "tempo": 20, "resultado": "aprovada"}
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect("127.0.0.1", 1883)
client.loop_start()
try:
    envio = client.publish("celulares/tutorial/eventos", json.dumps(evento), qos=1)
    envio.wait_for_publish(timeout=10)
    if not envio.is_published():
        raise TimeoutError("O broker não confirmou o recebimento.")
    print("Broker confirmou o recebimento do exemplo.")
finally:
    client.disconnect()
    client.loop_stop()
