import json
import hashlib
import sqlite3
from pathlib import Path

DB = Path(__file__).with_name("processo.sqlite3")
# Hipóteses didáticas em segundos; validar com medições da linha.
SMT_PROCESS = [
    ("Impressora de pasta", 15), ("SPI", 5),
    ("Pick & Place 1", 12), ("Pick & Place 2", 12),
    ("Pick & Place 3", 12), ("Pick & Place 4", 12),
    ("Pick & Place 5", 12), ("Forno de refusão", 180),
    ("AOI", 5), ("Saída SMT", 1),
]
MANUAL_PROCESS = [
    ("Gravação de FW", 14), ("PCBA no chassi", 18), ("Display", 16),
    ("Bateria", 27), ("Alto-falante", 15), ("Microfone", 21),
    ("Câmera traseira", 24), ("Câmera frontal", 13),
    ("Botões e vibra", 22), ("Tampa traseira", 17),
    ("Teste funcional", 26), ("Embalagem", 19),
]
PROCESS = SMT_PROCESS + MANUAL_PROCESS
STATIONS = [name for name, _ in PROCESS]
CAPACITIES = {name: (9 if name == "Forno de refusão" else 1) for name in STATIONS}
# Compatibilidade com as primeiras execuções do protótipo.
LEGACY_STATIONS = ["SMT"] + [name for name, _ in MANUAL_PROCESS]


def connect():
    conn = sqlite3.connect(DB, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE IF NOT EXISTS eventos (id_evento TEXT PRIMARY KEY, execucao TEXT, id_peca TEXT, estacao TEXT, tempo_simulado REAL, evento TEXT, resultado TEXT)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_execucao_tempo ON eventos(execucao, tempo_simulado)")
    if "detalhes" not in {row[1] for row in conn.execute("PRAGMA table_info(eventos)")}:
        conn.execute("ALTER TABLE eventos ADD COLUMN detalhes TEXT")
    if "sequencia" not in {row[1] for row in conn.execute("PRAGMA table_info(eventos)")}:
        conn.execute("ALTER TABLE eventos ADD COLUMN sequencia INTEGER")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_eventos_sequencia ON eventos(execucao, sequencia) WHERE sequencia IS NOT NULL")
    conn.execute("CREATE TABLE IF NOT EXISTS execucoes (execucao TEXT PRIMARY KEY, status TEXT, esperados INTEGER, recebidos INTEGER, resumo TEXT, digest TEXT, transporte TEXT)")
    conn.commit()
    return conn

def validate_event(event):
    fields = ("id_evento", "execucao", "id_peca", "estacao", "tempo_simulado", "evento", "resultado")
    if not isinstance(event, dict) or any(k not in event for k in fields):
        raise ValueError("Evento incompleto")
    if event["estacao"] not in STATIONS + LEGACY_STATIONS or event["evento"] not in ("fila", "entrada", "saida"):
        raise ValueError("Estação ou evento inválido")
    if event["resultado"] not in ("pendente", "aprovada", "reprovada") or not isinstance(event["tempo_simulado"], (int, float)) or event["tempo_simulado"] < 0:
        raise ValueError("Resultado ou tempo inválido")
    import math
    if not math.isfinite(event["tempo_simulado"]):
        raise ValueError("Tempo não finito")
    if "sequencia" in event and (type(event["sequencia"]) is not int or event["sequencia"] < 0):
        raise ValueError("Sequência inválida")
    return fields


def save_many(conn, events):
    # Valida o lote inteiro antes da primeira escrita: confirmação só após COMMIT.
    rows = []
    has_sequence = "sequencia" in {r[1] for r in conn.execute("PRAGMA table_info(eventos)")}
    for event in events:
        fields = validate_event(event)
        row = tuple(event[k] for k in fields) + (json.dumps(event.get("detalhes", {}), ensure_ascii=False),)
        rows.append(row + (event.get("sequencia"),) if has_sequence else row)
    columns = "id_evento,execucao,id_peca,estacao,tempo_simulado,evento,resultado,detalhes" + (",sequencia" if has_sequence else "")
    placeholders = ",".join("?" for _ in range(9 if has_sequence else 8))
    with conn:
        conn.executemany(f"INSERT INTO eventos ({columns}) VALUES ({placeholders}) ON CONFLICT(id_evento) DO NOTHING", rows)


def save(conn, event):
    save_many(conn, [event])


def summarize_events(events):
    started = len({e["id_peca"] for e in events})
    finished = sum(e["evento"] == "saida" and e["estacao"] == "Embalagem" for e in events)
    rejected = sum(e["resultado"] == "reprovada" for e in events)
    return dict(iniciadas=started, concluidas=finished, retidas_reprovadas=rejected,
                em_processo=started-finished-rejected)


def make_manifest(events):
    return dict(tipo="fim_execucao", execucao=events[0]["execucao"], esperados=len(events),
                digest=hashlib.sha256("\n".join(e["id_evento"] for e in events).encode()).hexdigest(),
                resumo=summarize_events(events))


def confirm_run(conn, manifest, transport):
    run = manifest["execucao"]
    rows = conn.execute("SELECT id_evento,sequencia,id_peca,estacao,evento,resultado FROM eventos WHERE execucao=? ORDER BY sequencia", (run,)).fetchall()
    expected = manifest["esperados"]
    if len(rows) != expected or any(r[1] != i for i,r in enumerate(rows)):
        raise ValueError(f"Histórico incompleto: {len(rows)} de {expected} eventos, ou sequência com lacunas")
    digest = hashlib.sha256("\n".join(r[0] for r in rows).encode()).hexdigest()
    if digest != manifest["digest"]:
        raise ValueError("Identificadores do banco diferem dos gerados")
    started = len({r[2] for r in rows})
    finished = sum(r[3] == "Embalagem" and r[4] == "saida" for r in rows)
    rejected = sum(r[5] == "reprovada" for r in rows)
    actual = dict(iniciadas=started, concluidas=finished, retidas_reprovadas=rejected,
                  em_processo=started-finished-rejected)
    if actual != manifest["resumo"]:
        raise ValueError("Resumo gravado diverge do resumo gerado")
    with conn:
        conn.execute("INSERT INTO execucoes VALUES (?,?,?,?,?,?,?) ON CONFLICT(execucao) DO UPDATE SET status=excluded.status,esperados=excluded.esperados,recebidos=excluded.recebidos,resumo=excluded.resumo,digest=excluded.digest,transporte=excluded.transporte",
                     (run,"validada",expected,len(rows),json.dumps(actual),digest,transport))
    return actual
