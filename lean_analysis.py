"""Hipótese local de balanceamento e indicadores derivados dos eventos."""
LEAN_TIMES = {"Bateria": 19, "Alto-falante": 19, "Microfone": 19}
LEAN_FULL_TIMES = {**LEAN_TIMES, "Câmera traseira": 19, "Câmera frontal": 18,
                   "Botões e vibra": 19, "Tampa traseira": 20,
                   "Teste funcional": 19, "Embalagem": 20}


def final_queues(events):
    latest = {}
    for event in events:
        latest[event["id_peca"]] = event
    queues = {}
    for event in latest.values():
        if event["evento"] == "fila":
            name = event["estacao"]
            queues[name] = queues.get(name, 0) + 1
    return queues


def summarize_flow(events, horizon):
    starts, queues, battery_waits = {}, {}, []
    lead_times = []
    battery_queue = battery_max = 0
    battery_area = previous = 0
    for event in events:
        t, piece = event["tempo_simulado"], event["id_peca"]
        starts.setdefault(piece, t)
        if event["estacao"] == "Bateria":
            battery_area += battery_queue * (t - previous)
            previous = t
            if event["evento"] == "fila":
                queues[piece] = t
                battery_queue += 1
                battery_max = max(battery_max, battery_queue)
            elif event["evento"] == "entrada":
                battery_waits.append(t - queues.pop(piece))
                battery_queue -= 1
        if event["estacao"] == "Embalagem" and event["evento"] == "saida":
            lead_times.append(t - starts[piece])
    battery_area += battery_queue * (horizon - previous)
    return {
        "fila_bateria_final": battery_queue,
        "fila_bateria_maxima": battery_max,
        "fila_bateria_media": battery_area / horizon if horizon else 0,
        "espera_bateria_media_s": sum(battery_waits) / len(battery_waits) if battery_waits else None,
        "lead_time_medio_s": sum(lead_times) / len(lead_times) if lead_times else None,
        "ng_teste": sum(e["estacao"] == "Teste funcional" and e["evento"] == "saida" and e["resultado"] == "reprovada" for e in events),
    }
