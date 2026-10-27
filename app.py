import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from trace_validation import validate_trace
from core import connect, STATIONS, PROCESS, MANUAL_PROCESS, LEGACY_STATIONS, CAPACITIES
from lean_analysis import summarize_flow, final_queues
from lean_analysis import LEAN_TIMES, LEAN_FULL_TIMES
from station_config import resolve_times

st.set_page_config(page_title="Gêmeo digital da linha de celulares", layout="wide")
st.markdown("""<style>
.stApp{background:#000;color:#dbe7ea}header[data-testid="stHeader"]{background:#000}
.block-container{max-width:1240px;padding-top:2rem;padding-bottom:1rem}
h1{font-family:Georgia,serif!important;font-size:29px!important;font-weight:600!important}
[data-testid="stCaptionContainer"]{color:#7f979d}
</style>""", unsafe_allow_html=True)
st.title("Gêmeo digital da linha de celulares")
st.caption("Cenário 08 · Polo Industrial de Manaus · SMT e 12 estações de montagem")
with st.expander("Novo balanceamento — editar tempos e simular", expanded=False):
    st.caption("Edite os segundos de cada estação. A alteração só vale para a nova simulação; históricos existentes permanecem iguais. Chegadas a cada 20 s e capacidades mantidas. O ciclo ideal do OEE continua sendo a referência comum definida abaixo.")
    base_name = st.selectbox("Começar com os tempos de", ["Original", "Lean local", "Lean ampliado"], key="time_base")
    base_times = resolve_times(base=LEAN_FULL_TIMES if base_name == "Lean ampliado" else LEAN_TIMES if base_name == "Lean local" else {})
    edited = st.data_editor(pd.DataFrame([{"Estação": name, "Tempo (s)": float(base_times[name])} for name, _ in PROCESS]), hide_index=True, disabled=["Estação"], num_rows="fixed", column_config={"Tempo (s)": st.column_config.NumberColumn(min_value=0.1, step=0.1)}, key="station_times_"+base_name)
    custom_times = dict(zip(edited["Estação"], edited["Tempo (s)"]))
    st.download_button("Baixar tempos em JSON", json.dumps(custom_times, ensure_ascii=False, indent=2), file_name="tempos-estacoes.json", mime="application/json")
    custom_name = st.text_input("Nome do novo cenário", value="Meu balanceamento")
    controls = st.columns(4)
    custom_hours = controls[0].number_input("Turno da nova simulação (h)", min_value=0.1, value=8.0, step=0.5)
    custom_seed = controls[1].number_input("Semente da nova simulação", min_value=0, value=7, step=1)
    custom_spi = controls[2].checkbox("SPI ativo", value=True)
    custom_aoi = controls[3].checkbox("AOI ativo", value=True)
    custom_rate = st.number_input("Probabilidade de defeito por origem", min_value=0.0, max_value=1.0, value=0.02, step=0.01)
    delivery = st.radio("Gravação da nova simulação", ["Direto no banco", "Via MQTT"], horizontal=True)
    st.caption("Via MQTT exige broker e coletor ativos. Inspeções usam detecção de 95%; mesma probabilidade de defeito para pasta, colocação e refusão. Este editor muda tempos, não valida a viabilidade física do método.")
    if st.button("Executar nova simulação", type="primary"):
        try:
            resolve_times(custom_times)
            if not custom_name.strip():
                raise ValueError("Dê um nome ao novo cenário.")
            root = Path(__file__).resolve().parent
            folder = root / "cenarios"
            folder.mkdir(exist_ok=True)
            profile = folder / (uuid.uuid4().hex + ".json")
            profile.write_text(json.dumps(custom_times, ensure_ascii=False, indent=2), encoding="utf-8")
            command = [sys.executable, str(root / "simulate.py"), "--tempos", str(profile), "--nome-cenario", custom_name.strip(), "--turno-horas", str(custom_hours), "--semente", str(custom_seed), "--defeitos", str(custom_rate)]
            if not custom_spi:
                command.append("--sem-spi")
            if not custom_aoi:
                command.append("--sem-aoi")
            if delivery == "Via MQTT":
                command.append("--mqtt")
            with st.spinner("Simulando e conferindo a gravação..."):
                result = subprocess.run(command, cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=180)
            if result.returncode:
                st.error("A simulação não foi confirmada. Confira a mensagem antes de executar novamente.")
                st.code(result.stderr or result.stdout)
            else:
                st.success("Novo histórico validado. Escolha seu nome nos seletores de cenários abaixo.")
                st.text(result.stdout)
        except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
            st.error(str(exc))
with st.expander("Hipóteses de custo da não qualidade"):
    st.caption("Estimativas para análise, sem alterar a simulação. Retenção não significa sucata; os valores representam o custo atribuído ao tratamento de cada ocorrência.")
    cost_columns = st.columns(4)
    spi_cost = cost_columns[0].number_input("Por retenção no SPI (R$)", min_value=0.0, value=15.0, step=5.0)
    aoi_cost = cost_columns[1].number_input("Por retenção no AOI (R$)", min_value=0.0, value=60.0, step=5.0)
    final_cost = cost_columns[2].number_input("Por reprovação final (R$)", min_value=0.0, value=240.0, step=10.0)
    unit_value = cost_columns[3].number_input("Valor de referência por placa (R$)", min_value=1.0, value=240.0, step=10.0)
mode = st.radio("Visualização", ["Reproduzir histórico", "Acompanhar ao vivo"], horizontal=True)

compare = st.toggle("Comparar dois cenários", value=True)
line_ideal_cycle = st.number_input("Ciclo ideal de referência da linha (s/peça)", min_value=0.1, value=20.0, step=0.5)
st.caption("OEE simplificado da linha = aprovadas na embalagem × ciclo ideal comum ÷ tempo planejado transcorrido. Referência inicial de 20 s: hipótese de capacidade do modelo, a validar; não é takt medido. NG = somente reprovações no teste funcional. Retenções SPI/AOI ficam separadas. Sem paradas modeladas: disponibilidade assumida em 100%.")


def read_scenario(conn, run, config):
    data = pd.read_sql_query("SELECT rowid AS ordem, id_evento, execucao, id_peca, estacao, tempo_simulado, evento, resultado FROM eventos WHERE execucao=? ORDER BY tempo_simulado, rowid", conn, params=(run,))
    modern = config.get("modelo") == "smt_v2"
    names = ([name for name in STATIONS if not (name == "SPI" and not config.get("spi", True))
              and not (name == "AOI" and not config.get("aoi", True))] if modern else
             [name for name in LEGACY_STATIONS if name in data.estacao.values])
    times = config.get("tempos", dict(PROCESS, SMT=20))
    capacities = config.get("capacidades", {name: 1 for name in names})
    events = [dict(t=row.tempo_simulado, p=row.id_peca, s=row.estacao,
                   e=row.evento, r=row.resultado) for row in data.itertuples()]
    gaps = validate_trace(events, names)
    receipt = conn.execute("SELECT status,esperados,recebidos FROM execucoes WHERE execucao=?", (run,)).fetchone()
    verified = bool(receipt and receipt[0] == "validada" and receipt[1] == receipt[2] == len(events))
    complete = not gaps and (receipt is None or verified)
    payload = dict(id=run, complete=complete, verified=verified, gaps=gaps, events=events, stations=names,
                   durations=[times[s] for s in names], capacities=[capacities.get(s, 1) for s in names],
                   manual=[s for s, _ in MANUAL_PROCESS],
                   end=(float(config["turno_segundos"]) if config.get("turno_segundos") and mode != "Acompanhar ao vivo" else float(data.tempo_simulado.max())),
                   live=mode == "Acompanhar ao vivo", costs={"SPI": spi_cost, "AOI": aoi_cost, "Teste funcional": final_cost, "unit": unit_value},
                   line_ideal_cycle=line_ideal_cycle)
    return data, payload


@st.fragment(run_every="2s" if mode == "Acompanhar ao vivo" else None)
def dashboard():
    conn = connect()
    try:
        registry = list(conn.execute("SELECT execucao, MIN(rowid) FROM eventos GROUP BY execucao ORDER BY MAX(rowid) DESC"))
        runs = [row[0] for row in registry]
        first_rows = dict(registry)
        if not runs:
            st.info("Execute o simulador para gerar os primeiros dados.")
            return
        certificates = {r[0]: r[1] for r in conn.execute("SELECT execucao,status FROM execucoes")}
        configs = {}
        for run_id in runs:
            raw = conn.execute("SELECT detalhes FROM eventos WHERE rowid=?", (first_rows[run_id],)).fetchone()[0]
            configs[run_id] = (json.loads(raw) if isinstance(raw, str) else {}).get("configuracao", {})
        def label(run_id):
            cfg = configs[run_id]
            quality = "✓ validada" if certificates.get(run_id) == "validada" else "recebendo" if certificates.get(run_id) == "recebendo" else "histórico sem confirmação final"
            if not cfg:
                return f"{run_id[:8]} · histórico inicial · {quality}"
            duration = f"{cfg['turno_segundos']/3600:g} h" if cfg.get("turno_segundos") else "por quantidade"
            return f"{run_id[:8]} · {cfg.get('cenario', 'Histórico')} · SPI {'ativo' if cfg.get('spi') else 'desligado'} · AOI {'ativo' if cfg.get('aoi') else 'desligado'} · {duration} · semente {cfg.get('semente', '—')} · {quality}"
        with st.expander("Estudo Lean — evolução do balanceamento", expanded=True):
            st.caption("Hipótese a validar: bateria 27→19 s; alto-falante 15→19 s; microfone 21→19 s. Mesmo número de recursos; demais tempos preservados. Não há FIFO limitado implementado.")
            st.caption("Lean ampliado: traseira/frontal 19/18 s; botões/tampa 19/20 s; teste/embalagem 19/20 s. Hipótese de redistribuição e eliminação de 6 s no conjunto teste/embalagem, sem reduzir a cobertura dos testes. Sem validação industrial.")
            study_seed = st.number_input("Semente do estudo", min_value=0, value=7, step=1)
            study_hours = st.number_input("Duração do estudo (h)", min_value=0.1, value=8.0, step=0.5)
            baseline = next((r for r in runs if certificates.get(r) == "validada" and configs[r].get("cenario") == "Atual" and configs[r].get("semente") == study_seed and configs[r].get("turno_segundos") == study_hours * 3600), None)
            rows = []
            for scenario in ("Atual", "SPI/AOI", "SPI/AOI + Lean", "SPI/AOI + Lean ampliado"):
                matched = next((r for r in runs if certificates.get(r) == "validada" and configs[r].get("cenario") == scenario and baseline and all(configs[r].get(k) == configs[baseline].get(k) for k in ("semente", "turno_segundos", "modelo", "defeito_pasta", "defeito_colocacao", "defeito_refusao", "deteccao_spi", "deteccao_aoi", "intervalo_chegada", "capacidades"))), None)
                if not matched:
                    st.info(f"Ainda falta uma execução validada de {scenario} nas condições escolhidas.")
                    continue
                raw_events = pd.read_sql_query("SELECT id_peca, estacao, tempo_simulado, evento, resultado FROM eventos WHERE execucao=? ORDER BY tempo_simulado, rowid", conn, params=(matched,)).to_dict("records")
                stats = summarize_flow(raw_events, configs[matched]["turno_segundos"])
                queues = final_queues(raw_events)
                finished = sum(e["estacao"] == "Embalagem" and e["evento"] == "saida" for e in raw_events)
                rejected = sum(e["resultado"] == "reprovada" for e in raw_events)
                started = len({e["id_peca"] for e in raw_events})
                rows.append({"Cenário": scenario, "Execução": matched[:8], "Concluídas": finished, "NG teste": stats["ng_teste"], "Retidas/reprovadas": rejected, "WIP final": started-finished-rejected, "Fila bateria final": stats["fila_bateria_final"], "Fila bateria máxima": stats["fila_bateria_maxima"], "Fila bateria média": round(stats["fila_bateria_media"], 2), "Espera bateria (min)": round(stats["espera_bateria_media_s"]/60, 2) if stats["espera_bateria_media_s"] is not None else None, "Lead time (min)": round(stats["lead_time_medio_s"]/60, 2) if stats["lead_time_medio_s"] is not None else None})
                rows[-1].update({"Fila câmera final": queues.get("Câmera traseira", 0), "Fila teste final": queues.get("Teste funcional", 0), "Total em filas final": sum(queues.values())})
                rows[-1]["OEE linha (%)"] = round(100*finished*line_ideal_cycle/configs[matched]["turno_segundos"], 2)
            if rows:
                st.dataframe(rows, hide_index=True)
                st.caption("Espera média: placas que iniciaram a bateria. Lead time: somente concluídas. Fila máxima inclui pedidos atendidos no mesmo instante. Os gráficos abaixo continuam comparando as duas execuções escolhidas.")
        if compare:
            preferred = sorted(runs, key=lambda r: certificates.get(r) != "validada")
            current = next((r for r in preferred if configs[r] and not configs[r].get("spi") and not configs[r].get("aoi")), runs[0])
            proposed = next((r for r in preferred if r != current and configs[r].get("spi") and configs[r].get("aoi")), next((r for r in runs if r != current), current))
            left, right = st.columns(2)
            a = left.selectbox("Cenário A — Atual", runs, index=runs.index(current), format_func=label, key="scenario_a")
            b = right.selectbox("Cenário B — Proposta", runs, index=runs.index(proposed), format_func=label, key="scenario_b")
            data_a, pa = read_scenario(conn, a, configs[a])
            data_b, pb = read_scenario(conn, b, configs[b])
            if a == b:
                st.info("A mesma execução foi escolhida nos dois seletores; as curvas serão iguais.")
            incomplete = [(name, scenario) for name, scenario in (("Atual", pa), ("Proposta", pb)) if not scenario['complete']]
            if incomplete:
                for name, scenario in incomplete:
                    st.error(f"{name}: execução incompleta ou ainda em recebimento. Não é válido comparar as concluídas deste histórico com o total do simulador. Selecione uma execução com ✓ validada.")
                return
            if pa['verified'] and pb['verified']:
                st.success(f"Dados conferidos no banco: Atual {len(pa['events']):,} eventos · Proposta {len(pb['events']):,} eventos. Totais iguais aos gerados pelo simulador.")
            if abs(pa['end'] - pb['end']) > 0.01:
                st.info("As durações são diferentes. A comparação usa somente o intervalo comum aos dois cenários.")
            keys = ("modelo", "semente", "defeito_pasta", "defeito_colocacao", "defeito_refusao", "intervalo_chegada")
            if any(configs[a].get(k) != configs[b].get(k) for k in keys):
                st.warning("As condições de entrada ou a versão do modelo diferem. Os resultados podem refletir essas diferenças além das mudanças nas inspeções.")
            payload = dict(scenarios=[pa, pb], end=min(pa['end'], pb['end']), live=mode == "Acompanhar ao vivo")
            template_name = "comparacao.html"
            st.caption("Atual em rosa · Proposta em verde · mesmo relógio e mesmas hipóteses de custo. Os rótulos identificam as execuções escolhidas; não modificam o modelo.")
            tables = [("Atual", data_a), ("Proposta", data_b)]
        else:
            run = st.selectbox("Execução registrada", runs, format_func=label, key="single_run")
            data, payload = read_scenario(conn, run, configs[run])
            if not payload['complete']:
                st.error("Execução incompleta ou em recebimento. Os gráficos e totais estão bloqueados para não apresentar valores menores como resultado final. Selecione uma execução com ✓ validada.")
                st.dataframe(data.tail(30), hide_index=True)
                return
            if payload['verified']:
                st.success(f"Execução validada: {len(payload['events']):,} eventos gerados e gravados no banco.")
            template_name = "painel.html"
            tables = [("Execução", data)]
    finally:
        conn.close()
    template = Path(__file__).with_name(template_name).read_text(encoding="utf-8")
    safe_json = json.dumps(payload, ensure_ascii=False).replace(chr(60), chr(92) + "u003c")
    components.html(template.replace("__PAYLOAD__", safe_json).replace("__METRICS_JS__", Path(__file__).with_name("metrics.js").read_text(encoding="utf-8")), height=2400 if compare else 2650, scrolling=True)
    with st.expander("Consultar eventos registrados"):
        for title, table in tables:
            st.caption(title)
            st.dataframe(table.drop(columns=["id_evento", "execucao", "ordem"]).tail(100), hide_index=True)


dashboard()
