import json
from pathlib import Path
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from trace_validation import validate_trace
from core import connect, STATIONS, PROCESS, MANUAL_PROCESS, LEGACY_STATIONS, CAPACITIES

st.set_page_config(page_title="Gêmeo digital da linha de celulares", layout="wide")
st.markdown("""<style>
.stApp{background:#000;color:#dbe7ea}header[data-testid="stHeader"]{background:#000}
.block-container{max-width:1240px;padding-top:2rem;padding-bottom:1rem}
h1{font-family:Georgia,serif!important;font-size:29px!important;font-weight:600!important}
[data-testid="stCaptionContainer"]{color:#7f979d}
</style>""", unsafe_allow_html=True)
st.title("Gêmeo digital da linha de celulares")
st.caption("Cenário 08 · Polo Industrial de Manaus · SMT e 12 estações de montagem")
with st.expander("Hipóteses de custo da não qualidade"):
    st.caption("Estimativas para análise, sem alterar a simulação. Retenção não significa sucata; os valores representam o custo atribuído ao tratamento de cada ocorrência.")
    cost_columns = st.columns(4)
    spi_cost = cost_columns[0].number_input("Por retenção no SPI (R$)", min_value=0.0, value=15.0, step=5.0)
    aoi_cost = cost_columns[1].number_input("Por retenção no AOI (R$)", min_value=0.0, value=60.0, step=5.0)
    final_cost = cost_columns[2].number_input("Por reprovação final (R$)", min_value=0.0, value=240.0, step=10.0)
    unit_value = cost_columns[3].number_input("Valor de referência por placa (R$)", min_value=1.0, value=240.0, step=10.0)
mode = st.radio("Visualização", ["Reproduzir histórico", "Acompanhar ao vivo"], horizontal=True)

compare = st.toggle("Comparar dois cenários", value=True)


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
                   functional_test_cycle=config.get("ciclo_ideal_teste_funcional", times.get("Teste funcional", dict(PROCESS)["Teste funcional"])))
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
            return f"{run_id[:8]} · SPI {'ativo' if cfg.get('spi') else 'desligado'} · AOI {'ativo' if cfg.get('aoi') else 'desligado'} · {duration} · semente {cfg.get('semente', '—')} · {quality}"
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
