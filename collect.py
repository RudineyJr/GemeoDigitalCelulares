import argparse
import json
import sqlite3
import paho.mqtt.client as mqtt
from core import connect, save, save_many, confirm_run


def handle_payload(conn,payload):
    if not isinstance(payload,dict):
        raise ValueError("Mensagem deve ser um objeto JSON")
    if payload.get("tipo")=="lote":
        events=payload["eventos"]
        run=payload["execucao"]
        if not events or len(events)>1000 or any(e["execucao"]!=run or type(e.get("sequencia")) is not int for e in events):
            raise ValueError("Lote inválido ou com execuções misturadas")
        if any(b["sequencia"]!=a["sequencia"]+1 for a,b in zip(events,events[1:])):
            raise ValueError("Lote fora de sequência")
        save_many(conn,events)
        with conn:
            conn.execute("INSERT INTO execucoes (execucao,status,transporte) VALUES (?,'recebendo','mqtt') ON CONFLICT(execucao) DO NOTHING",(run,))
        return dict(ok=True,salvos=len(events))
    if payload.get("tipo")=="fim_execucao":
        actual=confirm_run(conn,payload,"mqtt")
        return dict(ok=True,recebidos=payload["esperados"],resumo=actual)
    save(conn,payload)  # Compatibilidade com o publicador antigo, sem certificado final.
    return None


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--host",default="localhost")
    args=parser.parse_args()
    conn=connect()
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    def on_connect(client,userdata,flags,reason,properties):
        if not reason.is_failure:client.subscribe("celulares/eventos",qos=1)
    def on_subscribe(*args):
        print("Coletor pronto: inscrição confirmada; gravação por lotes e confirmação após COMMIT.",flush=True)
    def on_message(client,userdata,message):
        payload=None
        try:
            payload=json.loads(message.payload)
            reply=handle_payload(conn,payload)
        except (ValueError,TypeError,KeyError,sqlite3.Error) as exc:
            conn.rollback()
            reply=dict(ok=False,erro=str(exc))
            print("Mensagem rejeitada: "+str(exc),flush=True)
        if isinstance(payload,dict) and payload.get("topico_resposta","").startswith("celulares/confirmacoes/") and reply is not None:
            client.publish(payload["topico_resposta"],json.dumps({**reply,"lote_id":payload.get("lote_id")}),qos=1)
    client.on_connect=on_connect
    client.on_subscribe=on_subscribe
    client.on_message=on_message
    client.connect(args.host,1883,60)
    try:client.loop_forever()
    finally:
        client.disconnect()
        conn.close()

if __name__=="__main__":main()
