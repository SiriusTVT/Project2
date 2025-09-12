"""
Introduction Manager Module for Adventure Time Game

Handles game introduction, character creation, and initial setup.
"""

import os
import sys
import time
from rich.console import Console
from utils import seleccionar_velocidad, typewriter, get_intro_lines
from audio_manager import play_intro_music, play_narration, stop_narration, play_effect


def mostrar_intro(console):
    """Muestra la introducción (usando typewriter) y solicita nombre y clase.

    Retorna (nombre, clase) si el jugador acepta, o None si decide no jugar / interrumpe.
    """
    # permitir al jugador seleccionar la velocidad de texto antes de mostrar la intro
    velocidad = seleccionar_velocidad(console)

    # opción para omitir la introducción narrativa
    try:
        omitir = input("¿Deseas omitir la introducción narrativa? (s/n): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print("Entrada interrumpida. Saliendo...", style="bold red")
        return None
    skip_intro = omitir.startswith('s')

    # intentar reproducir música de fondo (INTRO-1.wav) después de seleccionar la velocidad
    audio_source = None
    _oal_quit = None
    try:
        # import local dentro de la función para que la ausencia de openal no rompa el programa
        from openal import oalInit, oalOpen, oalQuit
        oalInit()
        _oal_quit = oalQuit
        audio_source = play_intro_music()
        if audio_source is None:
            console.print(f"[yellow]Archivo de música no encontrado[/]")
    except Exception as e:
        # no fallar si openal no está instalado o hay problema con audio; intentar winsound en Windows
        try:
            if sys.platform.startswith("win"):
                audio_source = play_intro_music()
                if audio_source is None:
                    console.print(f"[yellow]Archivo de música no encontrado[/]")
            else:
                console.print(f"[yellow]Audio no disponible ({e}). Continuando sin música.[/]")
        except Exception:
            console.print(f"[yellow]Audio no disponible ({e}). Continuando sin música.[/]")

    # referencia a narración para poder detenerla
    narr_source = None
    narr_winsound = False

    if not skip_intro:
        # Reproducir narración (NARRADOR.wav) si existe
        try:
            narr_source, narr_winsound = play_narration()
        except Exception:
            pass
        # continuar con la introducción
        for parte in get_intro_lines():
            typewriter(parte, console=console, style="bold green")
            # pausa entre párrafos proporcional a la velocidad (más rápida -> menos pausa)
            from utils import TEXT_SPEED
            time.sleep(max(0.15, 0.45 * (velocidad / TEXT_SPEED)))

    # preguntar si el jugador está listo (si no se omitió la intro)
    if not skip_intro:
        try:
            respuesta = input("¿Estás listo para la aventura? (s/n): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            # detener narración antes de salir
            stop_narration(narr_source, narr_winsound)
            console.print("Entrada interrumpida. Saliendo...", style="bold red")
            return None
        if not respuesta or not respuesta.startswith('s'):
            # detener narración antes de terminar
            stop_narration(narr_source, narr_winsound)
            console.print("No estás listo para la aventura. Hasta la próxima.", style="yellow")
            return None
        # detener narración al iniciar la aventura
        stop_narration(narr_source, narr_winsound)
        console.print("¡Perfecto! La aventura comienza...", style="bold magenta")
    else:
        console.print("[dim]Introducción omitida. Pasando a la configuración del personaje...[/]")

    # pedir datos del aventurero (la música sigue hasta completar la configuración)
    try:
        nombre = input("Introduce el nombre de tu aventurero: ").strip()
    except (KeyboardInterrupt, EOFError):
        console.print("Entrada interrumpida. Saliendo...", style="bold red")
        return None

    if not nombre:
        nombre = "Aventurero"

    # Selección de clase con colores
    clases_validas = {
        'guerrero': 'bold red',
        'mago': 'bold blue',
        'explorador': 'bold green',
        'ladron': 'bold yellow'
    }
    while True:
        try:
            console.print("\nElige una clase:")
            for cname, style in clases_validas.items():
                desc = {
                    'guerrero': 'Alta salud y fuerza estable',
                    'mago': 'Baja salud, alto daño explosivo',
                    'explorador': 'Balanceado y versátil',
                    'ladron': 'Rápido con daño crítico'
                }.get(cname, '')
                # Usar etiqueta de apertura y cierre explícita para estilos compuestos
                console.print(f"  • [{style}]{cname.title()}[/{style}] - {desc}")
            clase = input("Clase (guerrero/mago/explorador/ladron): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("Entrada interrumpida. Saliendo...", style="bold red")
            try:
                if audio_source:
                    audio_source.stop()
                if _oal_quit:
                    _oal_quit()
            except Exception:
                pass
            return None
        if clase in clases_validas:
            sel_style = clases_validas[clase]
            console.print(f"Has elegido: [{sel_style}]{clase.title()}[/{sel_style}]", style="bold white")
            break
        else:
            console.print("Clase no válida. Intenta nuevamente.", style="bold red")

    # el jugador ya configuró el personaje

    # reproducir efecto de selección al terminar la configuración del personaje
    # usar únicamente el archivo exacto del proyecto
    select_rel = os.path.join(os.path.dirname(__file__), "Sound Effects", "SELECT1-1.wav")

    try:
        # En Windows, usar winsound primero (más fiable para efectos cortos)
        if sys.platform.startswith("win"):
            try:
                if os.path.exists(select_rel):
                    play_effect(select_rel)
                    time.sleep(2)
                else:
                    console.print(f"[yellow]Archivo de sonido no encontrado: {select_rel}[/]")
            except Exception as e:
                console.print(f"[yellow]winsound falló ({e}), intentando openal...[/]")
                raise
        else:
            # No-Windows: intentar openal
            from openal import oalOpen
            if os.path.exists(select_rel):
                try:
                    play_effect(select_rel, allow_winsound=False)
                    time.sleep(0.25)
                except Exception:
                    console.print(f"[yellow]No se pudo reproducir el efecto con openal: {select_rel}[/]")
            else:
                console.print(f"[yellow]Archivo de sonido no encontrado: {select_rel}[/]")
    except Exception:
        # fallback final: informar y continuar
        console.print("[yellow]Efecto de sonido no disponible (openal/winsound).[/]")

    # al terminar la configuración del personaje, detener la música de fondo si se está reproduciendo
    try:
        if audio_source:
            audio_source.stop()
        if _oal_quit:
            _oal_quit()
    except Exception:
        pass

    return (nombre, clase)