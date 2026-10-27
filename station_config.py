"""Configuração validada dos tempos, compartilhada pelo painel e simulador."""
import math
from core import PROCESS


def resolve_times(overrides=None, base=None):
    times = dict(PROCESS)
    times.update(base or {})
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise ValueError("Os tempos devem ser um objeto com nome da estação e segundos.")
        unknown = set(overrides) - set(times)
        if unknown:
            raise ValueError(f"Estações desconhecidas: {', '.join(sorted(unknown))}")
        times.update(overrides)
    for name, value in times.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"Tempo de {name}: informe um número positivo e finito.")
    if times["Forno de refusão"] < 20:
        raise ValueError("Neste modelo, a permanência no forno deve ser pelo menos 20 s (intervalo de entrada).")
    return times
