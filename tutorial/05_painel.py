r"""Abra com: .\.venv\Scripts\python -m streamlit run tutorial/05_painel.py --server.port 8503"""
import sqlite3
from pathlib import Path
import streamlit as st

st.title("Meu primeiro painel da simulação")
destino = Path(__file__).with_name("aprendizado.sqlite3")
if not destino.exists():
    st.info("Execute primeiro o exercício 04_eventos_e_banco.py.")
    st.stop()

with sqlite3.connect(destino) as banco:
    linhas = banco.execute("SELECT tempo, placa, evento FROM eventos ORDER BY tempo, rowid").fetchall()

saidas = [linha for linha in linhas if linha[2] == "saida"]
st.metric("Placas concluídas", len(saidas))
st.dataframe([dict(tempo=t, placa=p, evento=e) for t, p, e in linhas])
st.line_chart([dict(segundos=0, concluidas=0)] + [dict(segundos=t, concluidas=i) for i, (t, _, _) in enumerate(saidas, 1)], x="segundos", y="concluidas")
