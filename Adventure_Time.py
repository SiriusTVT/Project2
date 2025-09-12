from rich.console import Console

# Entrada principal del juego modularizado: orquesta la introducción, creación del personaje,
# construcción de escenas, arranque del motor y música de fondo.

from intro_manager import mostrar_intro
from character import Personaje
from scenes import crear_escenas
from game_engine import Juego
from audio_manager import play_bg_music
import utils as _utils


def main():
    console = Console()
    console.print("¡Bienvenido a Adventure Time!", style="bold cyan")

    # 1) Introducción y configuración del personaje
    intro = mostrar_intro(console)
    if not intro:
        return
    nombre, clase = intro

    # 2) Crear personaje y mostrar estadísticas iniciales (mismo estilo de antes)
    pj = Personaje(nombre, clase)
    console.print("\n— Estadísticas del aventurero —", style="bold white")
    console.print(f"Nombre: [cyan]{pj.nombre}[/]")
    console.print(f"Clase: [magenta]{pj.clase.title()}[/]")
    console.print(f"Salud: [green]{pj.salud}[/]")
    console.print(f"Daño: [yellow]{pj.danio}[/]")
    console.print(f"Habilidad especial: [bold]{pj.poder}[/]")
    console.print(f"Monedas: [yellow]{pj.monedas}[/]")

    # 3) Construir escenas y crear motor del juego
    escenas = crear_escenas()
    juego = Juego(pj, escenas, "inicio")

    # Mantener referencia global para utilidades que la consultan
    try:
        _utils.JUEGO_REF = juego
    except Exception:
        pass

    # 4) Iniciar música de aventura (OpenAL si es posible; si no, winsound en Windows)
    try:
        play_bg_music()
    except Exception:
        pass

    # 5) Ejecutar bucle principal
    juego.run()


if __name__ == "__main__":
    main()