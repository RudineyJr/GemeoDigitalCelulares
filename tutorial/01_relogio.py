r"""Execute a partir da pasta principal: .\.venv\Scripts\python tutorial/01_relogio.py"""
import simpy


def placa(env):
    print(f"{env.now:>3}s: placa entra na impressora")
    yield env.timeout(15)
    print(f"{env.now:>3}s: placa sai da impressora")


env = simpy.Environment()
env.process(placa(env))
env.run()
