import argparse
import json
import math
import random
import time
import uuid
import simpy
from core import connect, save_many, summarize_events, make_manifest, confirm_run, STATIONS, PROCESS, CAPACITIES
from lean_analysis import LEAN_TIMES, LEAN_FULL_TIMES
from station_config import resolve_times


def simulate(count=30, seed=7, defect_rate=0.02, emit=None, realtime=False,
             spi_enabled=True, aoi_enabled=True, spi_detection=0.95,
             aoi_detection=0.95, placement_rate=None, reflow_rate=None, shift_hours=None,
             lean=False, lean_full=False, station_times=None, scenario_name=None):
    """Modela placas concorrentes, inspeções e forno com nove posições.

    defect_rate: defeitos de pasta; os demais tipos usam esta taxa quando omitidos.
    Inspeções sem falsos positivos; retidas saem para análise externa, sem retorno.
    """
    placement_rate = defect_rate if placement_rate is None else placement_rate
    reflow_rate = defect_rate if reflow_rate is None else reflow_rate
    if count < 1 or any(not 0 <= value <= 1 for value in
                        (defect_rate, placement_rate, reflow_rate, spi_detection, aoi_detection)):
        raise ValueError("Quantidade positiva e probabilidades entre zero e um são obrigatórias")
    horizon = None
    if shift_hours is not None:
        if not math.isfinite(shift_hours) or shift_hours <= 0:
            raise ValueError("Duração do turno deve ser positiva e finita")
        horizon = shift_hours * 3600
        count = math.ceil(horizon / 20)
    env = simpy.Environment()
    lean = lean or lean_full
    overrides = LEAN_FULL_TIMES if lean_full else LEAN_TIMES if lean else {}
    times = resolve_times(station_times, overrides)
    process = [(name, times[name]) for name, _ in PROCESS]
    rng = random.Random(seed)
    run = uuid.uuid4().hex
    resources = {name: simpy.Resource(env, capacity=CAPACITIES[name]) for name in STATIONS}
    # A entrada no forno respeita distância mínima entre placas, além das posições.
    oven_gate = simpy.Resource(env, capacity=1)
    config = dict(turno_segundos=horizon, modelo="smt_v2", spi=spi_enabled, aoi=aoi_enabled,
                  defeito_pasta=defect_rate, defeito_colocacao=placement_rate,
                  defeito_refusao=reflow_rate, deteccao_spi=spi_detection,
                  deteccao_aoi=aoi_detection, semente=seed,
                  capacidades=CAPACITIES, tempos=dict(process), intervalo_chegada=20,
                  balanceamento_lean=lean,
                  balanceamento_lean_completo=lean_full,
                  ciclo_ideal_teste_funcional=dict(process)["Teste funcional"],
                  cenario=("SPI/AOI + Lean ampliado" if lean_full else "SPI/AOI + Lean" if lean else "SPI/AOI" if spi_enabled and aoi_enabled else "Atual" if not spi_enabled and not aoi_enabled else "Inspeções parciais"),
                  intervalo_entrada_forno=20, destino_retidas="análise externa, sem retorno")
    events = []
    if scenario_name:
        config["cenario"] = str(scenario_name).strip()
    config["tempos_personalizados"] = station_times is not None

    def record(piece, station, kind, result="pendente", reason=None):
        e = dict(id_evento=uuid.uuid4().hex, sequencia=len(events), execucao=run, id_peca=piece,
                 estacao=station, tempo_simulado=env.now, evento=kind, resultado=result,
                 detalhes=dict(configuracao=config, motivo=reason) if not events else dict(motivo=reason))
        events.append(e)
        if emit:
            emit(e)

    def piece_flow(number, draws):
        piece = f"P{number:04d}"
        defects = []
        for station, duration in process:
            if station == "SPI" and not spi_enabled:
                continue
            if station == "AOI" and not aoi_enabled:
                continue
            record(piece, station, "fila")
            # O forno é contínuo: entrada espaçada, permanência de 180 s,
            # até nove placas simultâneas. O espaçamento não trava a permanência.
            if station == "Forno de refusão":
                with oven_gate.request() as gate:
                    yield gate
                    request = resources[station].request()
                    yield request
                    record(piece, station, "entrada")
                    start = env.now
                    yield env.timeout(20)
                yield env.timeout(max(0, duration - (env.now - start)))
                if draws[2] < reflow_rate:
                    defects.append("refusão")
                record(piece, station, "saida")
                resources[station].release(request)
                continue
            with resources[station].request() as request:
                yield request
                record(piece, station, "entrada")
                yield env.timeout(duration)
                if station == "Impressora de pasta" and draws[0] < defect_rate:
                    defects.append("pasta")
                if station == "Pick & Place 5" and draws[1] < placement_rate:
                    defects.append("colocação")
                rejected = ((station == "SPI" and "pasta" in defects and draws[3] < spi_detection)
                            or (station == "AOI" and bool(defects) and draws[4] < aoi_detection)
                            or (station == "Teste funcional" and bool(defects)))
                # Aprovação em inspeção significa "não detectado", sem revelar
                # ao painel o defeito latente que só o simulador conhece.
                inspected = station in ("SPI", "AOI", "Teste funcional", "Embalagem")
                record(piece, station, "saida",
                       "reprovada" if rejected else "aprovada" if inspected else "pendente",
                       ", ".join(defects) if rejected else None)
                if rejected:
                    return

    def source():
        for n in range(1, count + 1):
            # Cinco sorteios por placa, iguais com ou sem inspeções para comparar cenários.
            env.process(piece_flow(n, [rng.random() for _ in range(5)]))
            yield env.timeout(20)

    env.process(source())
    if realtime:
        start = time.monotonic()
        while env.peek() != float("inf") and (horizon is None or env.peek() < horizon):
            delay = start + env.peek() - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            env.step()
        if horizon is not None:
            remaining = start + horizon - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)
    else:
        env.run(until=horizon) if horizon is not None else env.run()
    return events


def main():
    parser = argparse.ArgumentParser(description="Simulador SMT e 12 estações de montagem")
    parser.add_argument("--pecas", type=int, default=30)
    parser.add_argument("--turno-horas", type=float, help="Encerra no fim do turno; substitui --pecas")
    parser.add_argument("--semente", type=int, default=7)
    parser.add_argument("--defeitos", type=float, default=0.02)
    parser.add_argument("--mqtt", action="store_true")
    parser.add_argument("--reenviar", help="Reenvia um arquivo transmissoes/*.jsonl sem simular novamente")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--tempo-real", action="store_true")
    parser.add_argument("--sem-spi", action="store_true")
    parser.add_argument("--sem-aoi", action="store_true")
    parser.add_argument("--deteccao-spi", type=float, default=0.95)
    parser.add_argument("--deteccao-aoi", type=float, default=0.95)
    parser.add_argument("--defeitos-colocacao", type=float)
    parser.add_argument("--defeitos-refusao", type=float)
    parser.add_argument("--lean", action="store_true", help="Hipótese: bateria, alto-falante e microfone com 19 s cada")
    parser.add_argument("--lean-completo", action="store_true", help="Inclui balanceamento de câmeras, botões, tampa, teste e embalagem; hipótese didática")
    parser.add_argument("--tempos", help="Arquivo JSON com nomes das estações e tempos em segundos; sobrepõe o perfil Lean")
    parser.add_argument("--nome-cenario", help="Nome para identificar o balanceamento no painel")
    args = parser.parse_args()
    if args.pecas < 1 or not 0 <= args.defeitos <= 1:
        parser.error("Peças deve ser positivo e defeitos deve estar entre 0 e 1")
    if args.reenviar:
        from mqtt_transport import replay_archive
        replay_archive(args.reenviar, args.host)
        return
    station_times = None
    if args.tempos:
        from pathlib import Path
        try:
            station_times = json.loads(Path(args.tempos).read_text(encoding="utf-8-sig"))
            resolve_times(station_times)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    from mqtt_transport import ReliablePublisher, archive_events
    publisher = ReliablePublisher(args.host, batch_size=1) if args.mqtt and args.tempo_real else None
    try:
        events = simulate(args.pecas, args.semente, args.defeitos,
                          publisher.emit if publisher else None, args.tempo_real,
                          spi_enabled=not args.sem_spi, aoi_enabled=not args.sem_aoi,
                          spi_detection=args.deteccao_spi, aoi_detection=args.deteccao_aoi,
                          placement_rate=args.defeitos_colocacao, reflow_rate=args.defeitos_refusao,
                          shift_hours=args.turno_horas, lean=args.lean, lean_full=args.lean_completo,
                          station_times=station_times, scenario_name=args.nome_cenario)
        manifest = make_manifest(events)
        if args.mqtt:
            if publisher is None:
                archive_events(events)
                publisher = ReliablePublisher(args.host, archive=False)
                for event in events:
                    publisher.emit(event)
            publisher.finish(manifest)
        else:
            archive_events(events)
            conn = connect()
            try:
                for offset in range(0,len(events),200):
                    save_many(conn,events[offset:offset+200])
                confirm_run(conn,manifest,"direto")
            finally:
                conn.close()
        print(f"Execução {events[0]['execucao']}: {len(events)} eventos gerados e confirmados no banco.")
        summary = summarize_events(events)
        print(f"Turno: {args.turno_horas or 'por quantidade'}; iniciadas: {summary['iniciadas']}; concluídas: {summary['concluidas']}; retidas/reprovadas: {summary['retidas_reprovadas']}; em processo: {summary['em_processo']}.")
    finally:
        if publisher:
            publisher.close()

if __name__ == "__main__":
    main()
