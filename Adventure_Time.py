from rich.console import Console
from intro_manager import mostrar_intro
from character import Personaje
from scenes import crear_escenas
from game_engine import Juego
from audio_manager import play_bg_music
import utils as _utils


def main():
    console = Console()
    console.print("¡Bienvenido a Adventure Time!", style="bold cyan")
    intro = mostrar_intro(console)
    if not intro:
        return
    nombre, clase = intro
    pj = Personaje(nombre, clase)
    console.print("\n— Estadísticas del aventurero —", style="bold white")
    console.print(f"Nombre: [cyan]{pj.nombre}[/]")
    console.print(f"Clase: [magenta]{pj.clase.title()}[/]")
    console.print(f"Salud: [green]{pj.salud}[/]")
    console.print(f"Daño: [yellow]{pj.danio}[/]")
    console.print(f"Habilidad especial: [bold]{pj.poder}[/]")
    console.print(f"Monedas: [yellow]{pj.monedas}[/]")
    escenas = crear_escenas()
    juego = Juego(pj, escenas, "inicio")
    try:
        _utils.JUEGO_REF = juego
    except Exception:
        pass
    try:
        play_bg_music()
    except Exception:
        pass
    juego.run()


if __name__ == "__main__":
    main()