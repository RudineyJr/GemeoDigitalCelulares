"""Simulação pequena com registro em SQLite separado do banco principal."""
import sqlite3
from pathlib import Path
import simpy


def executar():
    destino = Path(__file__).with_name("aprendizado.sqlite3")
    env = simpy.Environment()
    maquina = simpy.Resource(env, capacity=1)
    # Este banco contém SOMENTE o exercício. Reexecutar substitui os dados dele.
    with sqlite3.connect(destino) as banco:
        banco.execute("CREATE TABLE IF NOT EXISTS eventos (tempo REAL, placa TEXT, evento TEXT)")
        banco.execute("DELETE FROM eventos")

        def registrar(placa, evento):
            banco.execute("INSERT INTO eventos VALUES (?, ?, ?)", (env.now, placa, evento))

        def processar(placa):
            registrar(placa, "fila")
            with maquina.request() as pedido:
                yield pedido
                registrar(placa, "entrada")
                yield env.timeout(15)
                registrar(placa, "saida")

        for numero in range(1, 4):
            env.process(processar(f"P{numero}"))
        env.run()
        banco.commit()
        for linha in banco.execute("SELECT * FROM eventos ORDER BY tempo, rowid"):
            print(linha)
    print(f"Banco do exercício: {destino}")


if __name__ == "__main__":
    executar()
