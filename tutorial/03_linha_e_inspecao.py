"""Miniatura didática; não reproduz as taxas ou todas as estações do projeto."""
import argparse
import random
import simpy


def simular(spi_ativo=True):
    env = simpy.Environment()
    sorteador = random.Random(7)
    etapas = [("Impressora", 15), ("SPI", 5), ("Teste funcional", 26)]
    maquinas = {nome: simpy.Resource(env, capacity=1) for nome, _ in etapas}
    total = {"iniciadas": 0, "concluidas": 0, "retidas_spi": 0, "ng_teste": 0}

    def placa(numero, defeituosa, sorteio_deteccao):
        total["iniciadas"] += 1
        for nome, duracao in etapas:
            if nome == "SPI" and not spi_ativo:
                continue
            with maquinas[nome].request() as pedido:
                yield pedido
                yield env.timeout(duracao)
                if nome == "SPI" and defeituosa and sorteio_deteccao < 0.95:
                    total["retidas_spi"] += 1
                    print(f"{env.now:>4}s: P{numero} retida no SPI")
                    return
                if nome == "Teste funcional" and defeituosa:
                    total["ng_teste"] += 1
                    print(f"{env.now:>4}s: P{numero} NG no teste")
                    return
        total["concluidas"] += 1
        print(f"{env.now:>4}s: P{numero} concluída")

    def gerar():
        for numero in range(1, 11):
            # Sempre dois sorteios por placa, mesmo se o SPI estiver desligado.
            defeituosa = sorteador.random() < 0.30
            deteccao = sorteador.random()
            env.process(placa(numero, defeituosa, deteccao))
            yield env.timeout(20)

    env.process(gerar())
    env.run()
    print(total)
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sem-spi", action="store_true")
    args = parser.parse_args()
    simular(spi_ativo=not args.sem_spi)
