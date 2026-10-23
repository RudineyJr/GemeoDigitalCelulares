def validate_trace(events, stations):
    """Detecta lacunas sem exigir saída das placas em processo no fim do turno."""
    previous = {}
    indexes = {name: i for i, name in enumerate(stations)}
    gaps = 0
    for event in events:
        before = previous.get(event["p"])
        kind, station = event["e"], event["s"]
        valid = False
        if kind == "fila":
            valid = (before is None and station == stations[0]) or (
                before is not None and before["e"] == "saida" and before["r"] != "reprovada"
                and indexes.get(station, -10) == indexes.get(before["s"], -20) + 1)
        elif kind == "entrada":
            valid = before is not None and before["e"] == "fila" and before["s"] == station
        elif kind == "saida":
            valid = before is not None and before["e"] == "entrada" and before["s"] == station
        gaps += not valid
        previous[event["p"]] = event
    return gaps
