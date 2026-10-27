"""Gera três históricos equivalentes; --mqtt usa o broker e o coletor existentes."""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Executa Atual, SPI/AOI e SPI/AOI + Lean")
    parser.add_argument("--mqtt", action="store_true")
    parser.add_argument("--turno-horas", type=float, default=8)
    parser.add_argument("--semente", type=int, default=7)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    for name, flags in [("Atual", ["--sem-spi", "--sem-aoi"]), ("SPI/AOI", []), ("SPI/AOI + Lean", ["--lean"]), ("SPI/AOI + Lean ampliado", ["--lean-completo"])]:
        print(f"\nGerando cenário: {name}", flush=True)
        command = [sys.executable, str(root / "simulate.py"), "--turno-horas", str(args.turno_horas), "--semente", str(args.semente), *flags]
        if args.mqtt:
            command.append("--mqtt")
        subprocess.run(command, cwd=root, check=True)


if __name__ == "__main__":
    main()
