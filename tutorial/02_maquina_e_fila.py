"""Três placas compartilham uma impressora. Os horários mostram a fila."""
import simpy


def placa(env, impressora, nome):
    print(f"{env.now:>3}s: {nome} chega à fila")
    with impressora.request() as pedido:
        yield pedido
        print(f"{env.now:>3}s: {nome} começa")
        yield env.timeout(15)
        print(f"{env.now:>3}s: {nome} termina")


def gerar(env, impressora):
    for numero in range(1, 4):
        env.process(placa(env, impressora, f"P{numero}"))
        yield env.timeout(10)


env = simpy.Environment()
impressora = simpy.Resource(env, capacity=1)
env.process(gerar(env, impressora))
env.run()
