from rich.console import Console
import time
import sys
import os

# velocidad por defecto para el efecto de "typewriter" (segundos por carácter)
# se puede ajustar con la función `seleccionar_velocidad`
TEXT_SPEED = 0.03

# Referencia global para música de combate para poder detenerla inmediatamente al derrotar al jugador
FIGHT_AUDIO_REF = {"src": None, "winsound": False}
# Referencias para audio de derrota (FAILBATTLE / LOSE)
DEFEAT_AUDIO = {"sources": [], "winsound": False}

# Conjuntos de terreno para sonido de pasos
TERRAIN_FOREST = {"inicio", "izquierda", "rio", "rugido", "encrucijada"}
TERRAIN_SOLID = {"cabaña", "cofre", "mapa", "pelea", "combate", "post_pelea", "montaña", "cueva", "final_heroico", "final_oscuro", "final_neutral"}

# Último efecto reproducido para evitar solapamientos
LAST_SFX = {"src": None, "winsound": False}

def play_effect(path: str, allow_winsound: bool = True) -> bool:
    """Reproduce un efecto deteniendo el anterior para evitar solapamientos.

    Prioriza OpenAL; si no está disponible usa winsound (si se permite y no se quiere preservar otro audio).
    """
    if not path or not os.path.exists(path):
        return False
    # Detener efecto anterior (solo efecto, no música de fondo)
    try:
        if LAST_SFX["src"] is not None:
            try:
                LAST_SFX["src"].stop()
            except Exception:
                pass
            LAST_SFX["src"] = None
        if LAST_SFX["winsound"]:
            if sys.platform.startswith("win"):
                try:
                    import winsound
                    winsound.PlaySound(None, 0)
                except Exception:
                    pass
            LAST_SFX["winsound"] = False
    except Exception:
        pass
    # Intentar OpenAL
    try:
        from openal import oalOpen
        try:
            src = oalOpen(path)
            if src is not None:
                src.play()
                LAST_SFX["src"] = src
                LAST_SFX["winsound"] = False
                return True
        except Exception:
            pass
    except Exception:
        pass
    # Fallback winsound
    if allow_winsound and sys.platform.startswith("win"):
        try:
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            LAST_SFX["src"] = None
            LAST_SFX["winsound"] = True
            return True
        except Exception:
            pass
    return False


def _play_sfx(filepath):
    """Reproduce un efecto de sonido corto de forma no bloqueante.

    Intenta OpenAL primero; si falla y es Windows, usa winsound.
    """
    try:
        from openal import oalOpen
        if os.path.exists(filepath):
            try:
                src = oalOpen(filepath)
                if src is not None:
                    src.play()
                    return True
            except Exception:
                pass
    except Exception:
        pass
    # Fallback Windows
    try:
        if sys.platform.startswith("win") and os.path.exists(filepath):
            import winsound
            winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True
    except Exception:
        pass
    return False


def seleccionar_velocidad(console):
    """Pregunta al usuario por la velocidad de texto y ajusta TEXT_SPEED.

    Retorna el valor numérico de la velocidad seleccionada.
    """
    global TEXT_SPEED
    console.print("Elige la velocidad de texto: [b]rápida[/] (r), [b]normal[/] (n), [b]lenta[/] (l)")
    try:
        resp = input("Velocidad (r/n/l, por defecto n): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print("Entrada interrumpida. Usando velocidad por defecto.", style="yellow")
        return TEXT_SPEED
    if resp.startswith('r'):
        TEXT_SPEED = 0.01
    elif resp.startswith('l'):
        TEXT_SPEED = 0.06
    else:
        TEXT_SPEED = 0.03

    console.print(f"Velocidad seleccionada: {TEXT_SPEED}s por carácter")
    return TEXT_SPEED

class Personaje:
    def __init__(self, nombre, clase=None, nivel=1):
        """Crea un personaje con nombre, clase, nivel y calcula salud y daño según la clase.

        Args:
            nombre (str): nombre del personaje
            clase (str|None): tipo de clase ('guerrero','mago','explorador'...)
            nivel (int): nivel inicial
        """
        self.nombre = nombre
        self.nivel = nivel
        self.clase = (clase or "explorador").lower()
        # atributo opcional usado por la historia
        self.tiene_piedra = False

        # definir estadísticas base por clase
        stats = {
            'guerrero': {'salud': 120, 'danio': 15},
            'mago': {'salud': 70, 'danio': 22},
            'explorador': {'salud': 90, 'danio': 12},
            'ladron': {'salud': 85, 'danio': 14},
        }
        # usar valores por defecto si la clase no existe
        base = stats.get(self.clase, {'salud': 80, 'danio': 10})
        # ajustar salud según nivel (por ejemplo +10 por nivel)
        self.salud = base['salud'] + (self.nivel - 1) * 10
        self.danio = base['danio'] + int((self.nivel - 1) * 1)

        self.salud_max = self.salud
        self.poderes = {
            'guerrero': 'Golpe fuerte',
            'mago': 'Bola de fuego',
            'explorador': 'Ataque rápido',
            'ladron': 'Ataque sigiloso',
        }
        self.poder = self.poderes.get(self.clase, 'Ataque básico')

    def restaurar(self):
        """Restaura el estado básico del personaje para reiniciar la aventura."""
        self.salud = self.salud_max
        # Reiniciar usos del poder especial si existían
        self.poder_usos = 2
        # Quitar progreso clave de la historia
        self.tiene_piedra = False

class Enemigo:
    def __init__(self, nombre="Bestia sombría", salud=80, danio=12):
        self.nombre = nombre
        self.salud = salud
        self.salud_max = salud
        self.danio = danio
    def esta_vivo(self):
        return self.salud > 0
    def mostrar(self, console):
        console.print(f"[bold red]{self.nombre}[/] - Salud: {self.salud}")

def combate(jugador):
    console = Console()
    enemigo = Enemigo()
    console.print("\n[bold red]¡Una bestia sombría aparece![/]")
    defensa = False
    if not hasattr(jugador, "poder_usos"):
        jugador.poder_usos = 2
    while jugador.salud > 0 and enemigo.salud > 0:
        console.print(f"\nTu salud: [green]{jugador.salud}[/] / {jugador.salud_max}")
        enemigo.mostrar(console)
        console.print("\nElige tu acción:")
        console.print("1. Atacar")
        console.print(f"2. Usar poder especial ({jugador.poder}) [{jugador.poder_usos} usos restantes]")
        console.print("3. Defender")
        console.print("4. Curarse (+15 salud)")
        accion = input("Acción (1-4): ").strip()
        if accion == "1":
            # Efecto de espada
            play_effect(os.path.join(os.path.dirname(__file__), "Player Effects", "SWORD-1.wav"))
            danio = jugador.danio
            console.print(f"Atacas y haces [yellow]{danio}[/] de daño.")
            enemigo.salud -= danio
        elif accion == "2":
            if jugador.poder_usos > 0:
                # Poder especial también usa efecto de espada
                play_effect(os.path.join(os.path.dirname(__file__), "Player Effects", "SWORD-1.wav"))
                danio = jugador.danio + 10
                console.print(f"Usas tu poder especial '{jugador.poder}' y haces [yellow]{danio}[/] de daño!")
                enemigo.salud -= danio
                jugador.poder_usos -= 1
            else:
                console.print("[dim]Ya no puedes usar tu poder especial.[/]")
        elif accion == "3":
            # Efecto de escudo al defender
            play_effect(os.path.join(os.path.dirname(__file__), "Player Effects", "SHIELD-1.wav"))
            console.print("Te preparas para defenderte. El daño recibido se reduce a la mitad este turno.")
            defensa = True
        elif accion == "4":
            curar = min(15, jugador.salud_max - jugador.salud)
            jugador.salud += curar
            console.print(f"Te curas [green]{curar}[/] puntos de salud.")
        else:
            console.print("[red]Acción no válida.[/]")
            continue
        # Turno del enemigo si sigue vivo
        if enemigo.salud > 0:
            import random
            ataque = random.choice(["normal", "fuerte"])
            if ataque == "normal":
                danio_enemigo = enemigo.danio
                mensaje = "La bestia te ataca."
            else:
                danio_enemigo = enemigo.danio + 5
                mensaje = "La bestia lanza un ataque feroz!"
            if defensa:
                danio_enemigo //= 2
                defensa = False
            jugador.salud -= danio_enemigo
            console.print(f"{mensaje} Recibes [red]{danio_enemigo}[/] de daño.")
        time.sleep(0.5)
    if jugador.salud > 0:
        console.print("\n[bold green]¡Has vencido a la bestia![/]")
        # reproducir sonido de victoria
        play_effect(os.path.join(os.path.dirname(__file__), "Sound Effects", "WINBATTLE-1.wav"))
    else:
        console.print("\n[bold red]La bestia te ha derrotado...[/]")
        # Detener música de pelea inmediatamente (openal o winsound)
        try:
            global FIGHT_AUDIO_REF
            if FIGHT_AUDIO_REF.get("src") is not None:
                try:
                    FIGHT_AUDIO_REF["src"].stop()
                except Exception:
                    pass
            if FIGHT_AUDIO_REF.get("winsound") and sys.platform.startswith("win"):
                try:
                    import winsound
                    winsound.PlaySound(None, 0)
                except Exception:
                    pass
            # limpiar referencia
            FIGHT_AUDIO_REF["src"] = None
            FIGHT_AUDIO_REF["winsound"] = False
        except Exception:
            pass
        # Reproducir sonidos de derrota simultáneamente (preferir openal)
        base_dir = os.path.dirname(__file__)
        fail_path = os.path.join(base_dir, "Music", "FAILBATTLE-1.wav")
        lose_path = os.path.join(base_dir, "Sound Effects", "LOSE-1.wav")
        played_openal = False
        defeat_winsound = False
        try:
            from openal import oalOpen
            fuentes = []
            for p in (fail_path, lose_path):
                if os.path.exists(p):
                    try:
                        s = oalOpen(p)
                        if s is not None:
                            s.play()
                            fuentes.append(s)
                    except Exception:
                        pass
            if fuentes:
                played_openal = True
                try:
                    from __main__ import DEFEAT_AUDIO
                    DEFEAT_AUDIO["sources"] = fuentes
                    DEFEAT_AUDIO["winsound"] = False
                except Exception:
                    pass
        except Exception:
            pass
        if not played_openal:
            # Fallback: reproducir en secuencia (winsound u otro) si no se pudo con openal
            play_effect(fail_path)
            play_effect(lose_path)
            if sys.platform.startswith("win"):
                defeat_winsound = True
                try:
                    from __main__ import DEFEAT_AUDIO
                    DEFEAT_AUDIO["sources"] = []
                    DEFEAT_AUDIO["winsound"] = True
                except Exception:
                    pass
        # Preguntar si se desea reiniciar la aventura
        while True:
            try:
                resp = input("¿Quieres intentarlo de nuevo desde el inicio? (s/n): ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                resp = 'n'
            if resp.startswith('s'):
                # detener sonidos de derrota antes de reiniciar
                try:
                    from __main__ import DEFEAT_AUDIO
                    for s in DEFEAT_AUDIO.get("sources", []):
                        try:
                            s.stop()
                        except Exception:
                            pass
                    if DEFEAT_AUDIO.get("winsound") and sys.platform.startswith("win"):
                        try:
                            import winsound
                            winsound.PlaySound(None, 0)
                        except Exception:
                            pass
                    DEFEAT_AUDIO["sources"] = []
                    DEFEAT_AUDIO["winsound"] = False
                except Exception:
                    pass
                if hasattr(jugador, 'restaurar'):
                    jugador.restaurar()
                return "reiniciar"  # indicador especial para el bucle del juego
            if resp.startswith('n') or resp == '':
                return "final_oscuro"
            console.print("[yellow]Opción no válida. Responde s o n.[/]")
    return "post_pelea"



def main():
    console = Console()
    console.print("¡Bienvenido a Adventure Time!", style="bold cyan")

    # mostrar la introducción y pedir nombre/clase al jugador
    intro = mostrar_intro(console)
    if not intro:
        # el jugador no quiso continuar o se interrumpió la entrada
        return

    nombre, clase = intro

    # crear personaje y mostrar estadísticas
    pj = Personaje(nombre, clase)
    console.print("\n— Estadísticas del aventurero —", style="bold white")  
    console.print(f"Nombre: [cyan]{pj.nombre}[/]")
    console.print(f"Clase: [magenta]{pj.clase.title()}[/]")
    console.print(f"Salud: [green]{pj.salud}[/]")
    console.print(f"Daño: [yellow]{pj.danio}[/]")
    console.print(f"Habilidad especial: [bold]{pj.poder}[/]")

    # crear escenas y lanzar el juego
    escenas = crear_escenas()
    juego = Juego(pj, escenas, "inicio")

    # iniciar música de aventura después de configurar el personaje
    try:
        from openal import oalInit, oalOpen, oalQuit
        oalInit()
        bg_path = os.path.join(os.path.dirname(__file__), "Music", "ADVENTURE-1.wav")
        if os.path.exists(bg_path):
            bg_src = oalOpen(bg_path)
            if bg_src is not None:
                # Reducir volumen al 20%
                try:
                    bg_src.set_gain(0.2)
                except Exception:
                    try:
                        bg_src.gain = 0.2
                    except Exception:
                        pass
                bg_src.play()
                console.print("[dim]Reproduciendo música de aventura...[/]")
                # guardar referencia para detener al final
                juego.bg_audio_source = bg_src
                juego.oal_quit = oalQuit
        else:
            console.print(f"[yellow]Archivo de música no encontrado: {bg_path}[/]")
    except Exception:
        # Fallback simple en Windows
        try:
            if sys.platform.startswith("win"):
                import winsound
                bg_path = os.path.join(os.path.dirname(__file__), "Music", "ADVENTURE-1.wav")
                if os.path.exists(bg_path):
                    winsound.PlaySound(bg_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    juego.winsound_used = True
                    console.print("[dim]Reproduciendo música de aventura (winsound)...[/]")
                else:
                    console.print(f"[yellow]Archivo de música no encontrado: {bg_path}[/]")
        except Exception:
            console.print("[yellow]No fue posible reproducir ADVENTURE-1.wav.[/]")
    juego.run()


def typewriter(text, delay=None, console=None, style=None):
    """Imprime `text` carácter por carácter para simular que alguien lo escribe.

    Args:
        text (str): cadena a imprimir.
        delay (float|None): segundos entre cada carácter. Si es None se usa `TEXT_SPEED`.
        console (rich.console.Console|None): consola para imprimir (si no se pasa, se crea una nueva).
        style (str|None): estilo para pasar a console.print.
    """
    if console is None:
        console = Console()
    # usar la velocidad global si no se pasa explícitamente
    if delay is None:
        delay = TEXT_SPEED
    # imprimir carácter a carácter sin saltos hasta terminar la línea
    for ch in text:
        # rich.Console.print acepta end, lo usamos para no añadir newline hasta el final
        console.print(ch, end="", style=style)
        time.sleep(delay)
    # terminar la línea
    console.print("")


def get_intro_lines():
    """Devuelve la lista de párrafos de la introducción.

    Esto permite reusar el mismo texto en la escena `inicio` y en la
    función que muestra la intro sin repetir cadenas.
    """
    return [
        "Abres los ojos lentamente y descubres que estás en medio de un bosque desconocido.",
        "No recuerdas cómo llegaste hasta aquí.",
        "El aire es frío, y alrededor solo escuchas el murmullo del viento entre los árboles y el canto lejano de algunos animales.",
        "Todo parece normal, pero pronto notas algo extraño: cada sonido tiene una dirección precisa, como si el bosque quisiera guiarte… o confundirte.",
        "A lo lejos, distingues un río que corre con fuerza, y hacia el otro lado, un sendero oculto entre la maleza.",
        "Tu instinto te dice que no estás solo. Hay algo, o alguien, observando tus pasos.",
        "El bosque guarda secretos antiguos y tú has sido arrastrado a este lugar para descubrirlos.",
        "Tu objetivo es encontrar la salida… o quizá algo más: un santuario oculto que parece ser la clave del destino de este lugar.",
        "Prepárate: cada decisión que tomes cambiará tu camino.",
        "El bosque puede llevarte a la libertad… o atraparte para siempre."
    ]


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
        # construir ruta absoluta a Music/INTRO-1.wav junto al script
        audio_path = os.path.join(os.path.dirname(__file__), "Music", "INTRO-1.wav")
        if os.path.exists(audio_path):
            audio_source = oalOpen(audio_path)
            if audio_source is not None:
                # Reducir volumen al 20% para la música de introducción (solo OpenAL)
                try:
                    audio_source.set_gain(0.2)
                except Exception:
                    try:
                        audio_source.gain = 0.2
                    except Exception:
                        pass
                audio_source.play()
        else:
            console.print(f"[yellow]Archivo de audio no encontrado: {audio_path}[/]")
    except Exception as e:
        # no fallar si openal no está instalado o hay problema con audio; intentar winsound en Windows
        try:
            if sys.platform.startswith("win"):
                import winsound
                audio_path = os.path.join(os.path.dirname(__file__), "Music", "INTRO-1.wav")
                if os.path.exists(audio_path):
                    winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                else:
                    console.print(f"[yellow]Archivo de audio no encontrado: {audio_path}[/]")
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
            narr_path = os.path.join(os.path.dirname(__file__), "Music", "NARRADOR.wav")
            if os.path.exists(narr_path):
                # intentar openal primero para no cortar la música intro
                try:
                    from openal import oalOpen
                    narr_source = oalOpen(narr_path)
                    if narr_source is not None:
                        narr_source.play()
                except Exception:
                    # fallback winsound (esto reemplazará la música intro si se usa winsound)
                    if sys.platform.startswith("win"):
                        try:
                            import winsound
                            winsound.PlaySound(narr_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                            narr_winsound = True
                        except Exception:
                            pass
        except Exception:
            pass
        # continuar con la introducción
        for parte in get_intro_lines():
            typewriter(parte, console=console, style="bold green")
            # pausa entre párrafos proporcional a la velocidad (más rápida -> menos pausa)
            time.sleep(max(0.15, 0.45 * (velocidad / TEXT_SPEED)))

    # preguntar si el jugador está listo (si no se omitió la intro)
    if not skip_intro:
        try:
            respuesta = input("¿Estás listo para la aventura? (s/n): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            # detener narración antes de salir
            try:
                if narr_source:
                    narr_source.stop()
                if narr_winsound and sys.platform.startswith("win"):
                    import winsound
                    winsound.PlaySound(None, 0)
            except Exception:
                pass
            console.print("Entrada interrumpida. Saliendo...", style="bold red")
            return None
        if not respuesta or not respuesta.startswith('s'):
            # detener narración antes de terminar
            try:
                if narr_source:
                    narr_source.stop()
                if narr_winsound and sys.platform.startswith("win"):
                    import winsound
                    winsound.PlaySound(None, 0)
            except Exception:
                pass
            console.print("No estás listo para la aventura. Hasta la próxima.", style="yellow")
            return None
        # detener narración al iniciar la aventura
        try:
            if narr_source:
                narr_source.stop()
            if narr_winsound and sys.platform.startswith("win"):
                import winsound
                winsound.PlaySound(None, 0)
        except Exception:
            pass
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

    try:
        clase = input("Elige una clase (guerrero/mago/explorador/ladron): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print("Entrada interrumpida. Saliendo...", style="bold red")
        # detener audio si estaba sonando
        try:
            if audio_source:
                audio_source.stop()
            if _oal_quit:
                _oal_quit()
        except Exception:
            pass
        return None

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


class Escena:
    def __init__(self, titulo, descripcion, opciones, sonido=None, accion=None):
        self.titulo = titulo
        self.descripcion = descripcion
        self.opciones = opciones
        self.sonido = sonido
        self.accion = accion

    def mostrar(self, console):
        console.print(f"\n[bold cyan]{self.titulo}[/]\n")
        typewriter(self.descripcion, console=console, style="green")
        if self.opciones:
            for i, opcion in enumerate(self.opciones.keys(), 1):
                console.print(f"[yellow]{i}[/]. {opcion}")

    def elegir(self, eleccion):
        try:
            opcion = list(self.opciones.keys())[int(eleccion)-1]
            return self.opciones[opcion]
        except Exception:
            return None


class Juego:
    def __init__(self, jugador, escenas, inicio):
        self.jugador = jugador
        self.escenas = escenas
        self.escena_actual = inicio
        self.console = Console()
        # referencias opcionales para audio de fondo
        self.bg_audio_source = None
        self.oal_quit = None
        self.winsound_used = False
        # referencia para sonido ambiente del río
        self.river_src = None
        self.river_winsound = False
        # referencias para música de combate
        self.fight_src = None
        self.fight_winsound = False

    def run(self):
        self.console.print("[bold magenta]¡Bienvenido a Adventure Time versión texto![/]")

        while True:
            escena = self.escenas[self.escena_actual]

            # Acción especial de la escena (si tiene)
            siguiente_accion = None
            if escena.accion:
                # Si vamos a entrar en combate, cambiar a música de pelea
                was_fight = (self.escena_actual == "combate")
                if was_fight:
                    try:
                        # detener música de aventura si está con openal
                        if self.bg_audio_source is not None:
                            try:
                                self.bg_audio_source.stop()
                            except Exception:
                                pass
                        # detener winsound de aventura si se usaba
                        if self.winsound_used and sys.platform.startswith("win"):
                            try:
                                import winsound
                                winsound.PlaySound(None, 0)
                            except Exception:
                                pass
                        # detener ambiente de río (openal / winsound)
                        try:
                            if self.river_src is not None:
                                try:
                                    self.river_src.stop()
                                except Exception:
                                    pass
                            self.river_src = None
                            if self.river_winsound and sys.platform.startswith("win"):
                                try:
                                    import winsound
                                    winsound.PlaySound(None, 0)
                                except Exception:
                                    pass
                            self.river_winsound = False
                        except Exception:
                            pass
                        # detener último efecto SFX para evitar solapamiento
                        try:
                            global LAST_SFX
                            if LAST_SFX.get("src") is not None:
                                try:
                                    LAST_SFX["src"].stop()
                                except Exception:
                                    pass
                                LAST_SFX["src"] = None
                            if LAST_SFX.get("winsound") and sys.platform.startswith("win"):
                                try:
                                    import winsound
                                    winsound.PlaySound(None, 0)
                                except Exception:
                                    pass
                            LAST_SFX["winsound"] = False
                        except Exception:
                            pass
                        # reproducir música de pelea
                        fight_path = os.path.join(os.path.dirname(__file__), "Music", "FIGHT-1.wav")
                        if os.path.exists(fight_path):
                            # preferir openal si el bg usa openal
                            if self.bg_audio_source is not None:
                                try:
                                    from openal import oalOpen
                                    f_src = oalOpen(fight_path)
                                    if f_src is not None:
                                        f_src.play()
                                        self.fight_src = f_src
                                        self.fight_winsound = False
                                        try:
                                            from __main__ import FIGHT_AUDIO_REF
                                            FIGHT_AUDIO_REF["src"] = f_src
                                            FIGHT_AUDIO_REF["winsound"] = False
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                            else:
                                # si bg era winsound, usar winsound para pelea
                                if sys.platform.startswith("win") and self.winsound_used:
                                    try:
                                        import winsound
                                        winsound.PlaySound(fight_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                                        self.fight_src = None
                                        self.fight_winsound = True
                                        try:
                                            from __main__ import FIGHT_AUDIO_REF
                                            FIGHT_AUDIO_REF["src"] = None
                                            FIGHT_AUDIO_REF["winsound"] = True
                                        except Exception:
                                            pass
                                    except Exception:
                                        # intentar openal como fallback
                                        try:
                                            from openal import oalOpen
                                            f_src = oalOpen(fight_path)
                                            if f_src is not None:
                                                f_src.play()
                                                self.fight_src = f_src
                                                self.fight_winsound = False
                                                try:
                                                    from __main__ import FIGHT_AUDIO_REF
                                                    FIGHT_AUDIO_REF["src"] = f_src
                                                    FIGHT_AUDIO_REF["winsound"] = False
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass
                    except Exception:
                        pass

                # ejecutar acción de la escena
                resultado = escena.accion(self.jugador)

                # Si veníamos de combate, detener música de pelea y reanudar aventura
                if was_fight:
                    try:
                        # detener música de pelea
                        try:
                            if self.fight_src is not None:
                                self.fight_src.stop()
                        except Exception:
                            pass
                        self.fight_src = None
                        # si la pelea usó winsound, reanudar aventura con winsound
                        # Solo reanudar música de aventura si NO se perdió (resultado != final_oscuro)
                        if resultado != "final_oscuro":
                            if self.fight_winsound and sys.platform.startswith("win"):
                                try:
                                    import winsound
                                    adv_path = os.path.join(os.path.dirname(__file__), "Music", "ADVENTURE-1.wav")
                                    if os.path.exists(adv_path):
                                        winsound.PlaySound(adv_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                                        # aseguramos la bandera de bg winsound
                                        self.winsound_used = True
                                    else:
                                        winsound.PlaySound(None, 0)
                                except Exception:
                                    pass
                            # si el bg era openal, reanudarlo solo si no es derrota
                            if self.bg_audio_source is not None:
                                try:
                                    self.bg_audio_source.play()
                                except Exception:
                                    pass
                        else:
                            # Derrota: detener explícitamente winsound de pelea si estaba activo
                            if self.fight_winsound and sys.platform.startswith("win"):
                                try:
                                    import winsound
                                    winsound.PlaySound(None, 0)
                                except Exception:
                                    pass
                        self.fight_winsound = False
                        # En caso de derrota, dejamos la música de aventura detenida.
                    except Exception:
                        pass

                if resultado:
                    siguiente_accion = resultado

            # Si la acción especial retorna una escena, saltar a esa escena directamente
            if siguiente_accion:
                # Manejo especial: reiniciar juego tras derrota
                if siguiente_accion == "reiniciar":
                    # Detener música de pelea si hubiera quedado algo sonando
                    try:
                        if self.fight_src is not None:
                            self.fight_src.stop()
                    except Exception:
                        pass
                    self.fight_src = None
                    self.fight_winsound = False
                    # Reanudar (o iniciar) música de aventura si estaba pausada por la pelea
                    try:
                        adv_path = os.path.join(os.path.dirname(__file__), "Music", "ADVENTURE-1.wav")
                        if self.bg_audio_source is not None:
                            # si existe fuente openal, reproducir
                            self.bg_audio_source.play()
                        else:
                            # si previamente se usó winsound para bg
                            if sys.platform.startswith("win"):
                                if self.winsound_used and os.path.exists(adv_path):
                                    import winsound
                                    winsound.PlaySound(adv_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    except Exception:
                        pass
                    # Reiniciar escena al inicio
                    self.escena_actual = "inicio"
                    continue
                self.escena_actual = siguiente_accion
                continue

            escena.mostrar(self.console)
            eleccion = input("\n¿Qué decides hacer?: ")
            siguiente = escena.elegir(eleccion)

            if not siguiente:
                self.console.print("[red]Opción no válida[/]")
                continue

            # Determinar texto exacto de la opción elegida para detectar acciones especiales (como cruzar el río)
            try:
                idx_op = int(eleccion) - 1
                claves_op = list(escena.opciones.keys())
                opcion_elegida_texto = claves_op[idx_op] if 0 <= idx_op < len(claves_op) else ""
            except Exception:
                opcion_elegida_texto = ""

            # Si estamos en la escena del río y se eligió "Cruzar el río", reproducir CROSSRIVER-1.wav
            try:
                if self.escena_actual == "rio":
                    try:
                        idx = int(eleccion) - 1
                        claves = list(escena.opciones.keys())
                        if 0 <= idx < len(claves):
                            opcion_texto = claves[idx].lower()
                        else:
                            opcion_texto = None
                    except Exception:
                        opcion_texto = None

                    if opcion_texto and "cruzar" in opcion_texto:
                        cr_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "CROSSRIVER-1.wav")
                        if os.path.exists(cr_path):
                            # Reproducir cruce de río con prioridad y pausar siguientes efectos breves
                            play_effect(cr_path)
                            # Marcar un timestamp para inhibir select/footstep inmediatos
                            self._last_crossriver_time = time.time()
            except Exception:
                pass

            # Si estamos saliendo del río, detener el ambiente del río
            try:
                if self.escena_actual == "rio" and siguiente != "rio":
                    # detener openal si existe
                    try:
                        if self.river_src is not None:
                            self.river_src.stop()
                    except Exception:
                        pass
                    self.river_src = None
                    # detener winsound si se usó para el río
                    if self.river_winsound and sys.platform.startswith("win"):
                        try:
                            import winsound
                            winsound.PlaySound(None, 0)
                        except Exception:
                            pass
                    self.river_winsound = False
            except Exception:
                pass

            # Reproducir sonido de selección al elegir una opción válida
            try:
                # Evitar solapar con CROSSRIVER si acaba de sonar hace < 0.4s
                recent_cross = hasattr(self, "_last_crossriver_time") and (time.time() - getattr(self, "_last_crossriver_time")) < 0.4
                if not recent_cross:
                    sfx_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "SELECT3-1.wav")
                    if os.path.exists(sfx_path):
                        play_effect(sfx_path)
            except Exception:
                pass

            # Reproducir sonido de pasos según el terreno del destino (evitar si es un final inmediato)
            try:
                if not siguiente.startswith("final"):
                    # No reproducir pasos si CROSSRIVER acaba de sonar (ventana 0.5s)
                    recent_cross = hasattr(self, "_last_crossriver_time") and (time.time() - getattr(self, "_last_crossriver_time")) < 0.5
                    cruzando = (self.escena_actual == "rio" and "cruzar" in opcion_elegida_texto.lower())
                    if not cruzando and not recent_cross:
                        base_dir = os.path.dirname(__file__)
                        step_path = os.path.join(base_dir, "Sound Effects", "FORESTWALK-1.wav") if siguiente in TERRAIN_FOREST else os.path.join(base_dir, "Sound Effects", "SOLIDWALK-1.wav")
                        if os.path.exists(step_path):
                            play_effect(step_path)
            except Exception:
                pass

            # Si el siguiente estado es 'rio', reproducir sonido de río y guardar referencia
            try:
                if siguiente == "rio":
                    river_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "RIVER-1.wav")
                    if os.path.exists(river_path):
                        # Preferir openal para no interrumpir música de fondo
                        try:
                            from openal import oalOpen
                            r_src = oalOpen(river_path)
                            if r_src is not None:
                                # reducir volumen al 20%
                                try:
                                    r_src.set_gain(0.2)
                                except Exception:
                                    try:
                                        r_src.gain = 0.2
                                    except Exception:
                                        pass
                                r_src.play()
                                # guardar referencia para poder detener luego
                                self.river_src = r_src
                                self.river_winsound = False
                        except Exception:
                            # En Windows, si NO se usa winsound para la música, usar winsound
                            if sys.platform.startswith("win") and not self.winsound_used:
                                try:
                                    import winsound
                                    winsound.PlaySound(river_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                                    # marcar que el río usa winsound para luego poder detenerlo
                                    self.river_src = None
                                    self.river_winsound = True
                                except Exception:
                                    pass
            except Exception:
                pass

            # Si la escena es un final, terminar
            if siguiente.startswith("final"):
                self.console.print("\n[bold red]--- FIN DEL JUEGO ---[/]\n")
                self.escenas[siguiente].mostrar(self.console)
                # detener música de fondo si existe y ambiente del río si estuviera activo
                try:
                    # pelea
                    try:
                        if self.fight_src is not None:
                            self.fight_src.stop()
                    except Exception:
                        pass
                    self.fight_src = None
                    if self.fight_winsound and sys.platform.startswith("win"):
                        try:
                            import winsound
                            winsound.PlaySound(None, 0)
                        except Exception:
                            pass
                    self.fight_winsound = False

                    # río (openal)
                    try:
                        if self.river_src is not None:
                            self.river_src.stop()
                    except Exception:
                        pass
                    self.river_src = None
                    # río (winsound)
                    if self.river_winsound and sys.platform.startswith("win"):
                        try:
                            import winsound
                            winsound.PlaySound(None, 0)
                        except Exception:
                            pass
                    self.river_winsound = False

                    if self.bg_audio_source:
                        self.bg_audio_source.stop()
                    if self.oal_quit:
                        self.oal_quit()
                    # detener winsound si se usó
                    if self.winsound_used and sys.platform.startswith("win"):
                        try:
                            import winsound
                            winsound.PlaySound(None, 0)
                        except Exception:
                            pass
                except Exception:
                    pass
                # terminar
                break

            self.escena_actual = siguiente


def crear_escenas():
    intro_text = "\n".join(get_intro_lines())
    return {
        "inicio": Escena(
            "Inicio Juego",
            "Toma tu primera decision",
            {"Explorar el sendero a la izquierda": "izquierda",
             "Avanzar hacia el río a la derecha": "rio"}
        ),

        "izquierda": Escena(
            "Árbol con marcas",
            "Llegas a un árbol con marcas extrañas en la corteza. El ambiente se siente más denso.",
            {"Tocar las marcas": "cabaña",
             "Ignorarlas y seguir adelante": "cabaña"}
        ),

        "rio": Escena(
            "Río caudaloso",
            "Encuentras un río caudaloso que fluye con fuerza.",
            {"Cruzar el río": "cabaña",
             "Caminar paralelo al río": "cabaña"}
        ),

        "cabaña": Escena(
            "Cabaña abandonada",
            "Llegas a una pequeña cabaña abandonada. La puerta de madera se mueve con el viento.",
            {"Entrar a la cabaña": "cofre",
             "Rodearla y seguir el camino": "rugido"}
        ),

        "cofre": Escena(
            "El cofre misterioso",
            "Dentro de la cabaña hay un cofre cerrado.",
            {"Abrir el cofre": "mapa",
             "Buscar pistas en el interior": "rugido"}
        ),

        "mapa": Escena(
            "Mapa secreto",
            "Encuentras un mapa con la ubicación de un santuario escondido.",
            {"Seguir el mapa": "encrucijada"},
            accion=lambda jugador: setattr(jugador, "tiene_piedra", True)
        ),

        "rugido": Escena(
            "El rugido lejano",
            "Sales de la cabaña y escuchas un rugido grave a lo lejos.",
            {"Seguir el rugido": "encrucijada"}
        ),

        "encrucijada": Escena(
            "La encrucijada",
            "Siguiendo tu camino llegas a una encrucijada. El viento sopla fuerte y las hojas crujen bajo tus pies.",
            {"Avanzar": "pelea"}
        ),
        "pelea": Escena(
            "¡Combate!",
            "Una bestia sombría bloquea tu camino. Debes luchar para avanzar.",
            {"Luchar": "combate"},
            accion=None
        ),
        "combate": Escena(
            "Combate contra la bestia",
            "¡Prepárate para pelear!",
            {},
            accion=combate
        ),
        "post_pelea": Escena(
            "Después del combate",
            "Tras vencer a la bestia, puedes elegir tu destino final.",
            {"Ir hacia la montaña": "montaña",
             "Ir hacia la cueva iluminada": "cueva"}
        ),

        "montaña": Escena(
            "El altar en la montaña",
            "Escalas entre rocas y descubres un altar antiguo. Sientes que aquí puedes colocar la piedra mágica.",
            {"Colocar la piedra": "final_heroico",
             "No colocar la piedra": "final_oscuro"}
        ),

        "cueva": Escena(
            "La cueva iluminada",
            "Encuentras a una criatura guardiana que te habla con voz grave.\nTe pregunta si deseas continuar tu viaje.",
            {"Aceptar la oferta del guardián": "final_neutral",
             "Rechazar y salir corriendo": "final_oscuro"}
        ),

        # finales
        "final_heroico": Escena(
            "Final Heroico",
            "Colocas la piedra en el altar. El bosque se ilumina y la magia oscura desaparece.\n¡Has salvado al bosque!",
            {}
        ),

        "final_oscuro": Escena(
            "Final Oscuro",
            "Decides no usar la piedra. La oscuridad crece y quedas atrapado para siempre...",
            {}
        ),

        "final_neutral": Escena(
            "Final Neutral",
            "Aceptas la oferta del guardián y te conviertes en el nuevo protector del bosque.",
            {}
        ),
    }

if __name__ == "__main__":
    main()