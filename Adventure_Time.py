from rich.console import Console
import time
import sys
import os

# velocidad por defecto para el efecto de "typewriter" (segundos por carácter)
# se puede ajustar con la función `seleccionar_velocidad`
TEXT_SPEED = 0.03


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
            danio = jugador.danio
            console.print(f"Atacas y haces [yellow]{danio}[/] de daño.")
            enemigo.salud -= danio
        elif accion == "2":
            if jugador.poder_usos > 0:
                danio = jugador.danio + 10
                console.print(f"Usas tu poder especial '{jugador.poder}' y haces [yellow]{danio}[/] de daño!")
                enemigo.salud -= danio
                jugador.poder_usos -= 1
            else:
                console.print("[dim]Ya no puedes usar tu poder especial.[/]")
        elif accion == "3":
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
    else:
        console.print("\n[bold red]La bestia te ha derrotado...[/]")
    if jugador.salud <= 0:
        return "final_oscuro"
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

    if not skip_intro:
        # (sin audio) continuar con la introducción
        for parte in get_intro_lines():
            typewriter(parte, console=console, style="bold green")
            # pausa entre párrafos proporcional a la velocidad (más rápida -> menos pausa)
            time.sleep(max(0.15, 0.45 * (velocidad / TEXT_SPEED)))

    # preguntar si el jugador está listo (si no se omitió la intro)
    if not skip_intro:
        try:
            respuesta = input("¿Estás listo para la aventura? (s/n): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print("Entrada interrumpida. Saliendo...", style="bold red")
            return None
        if not respuesta or not respuesta.startswith('s'):
            console.print("No estás listo para la aventura. Hasta la próxima.", style="yellow")
            return None
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
                import winsound
                if os.path.exists(select_rel):
                    winsound.PlaySound(select_rel, winsound.SND_FILENAME | winsound.SND_ASYNC)
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
                    sel_src = oalOpen(select_rel)
                    if sel_src is not None:
                        sel_src.play()
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

    def run(self):
        self.console.print("[bold magenta]¡Bienvenido a Adventure Time versión texto![/]")

        while True:
            escena = self.escenas[self.escena_actual]

            # Acción especial de la escena (si tiene)
            siguiente_accion = None
            if escena.accion:
                resultado = escena.accion(self.jugador)
                if resultado:
                    siguiente_accion = resultado

            # Si la acción especial retorna una escena, saltar a esa escena directamente
            if siguiente_accion:
                self.escena_actual = siguiente_accion
                continue

            escena.mostrar(self.console)
            eleccion = input("\n¿Qué decides hacer?: ")
            siguiente = escena.elegir(eleccion)

            if not siguiente:
                self.console.print("[red]Opción no válida[/]")
                continue

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
                            # Preferir openal si hay bg con openal; evitar interrumpir winsound de fondo
                            if self.bg_audio_source is not None:
                                try:
                                    from openal import oalOpen
                                    cr_src = oalOpen(cr_path)
                                    if cr_src is not None:
                                        cr_src.play()
                                except Exception:
                                    pass
                            else:
                                if sys.platform.startswith("win") and not self.winsound_used:
                                    try:
                                        import winsound
                                        winsound.PlaySound(cr_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                                    except Exception:
                                        try:
                                            from openal import oalOpen
                                            cr_src = oalOpen(cr_path)
                                            if cr_src is not None:
                                                cr_src.play()
                                        except Exception:
                                            pass
                                else:
                                    try:
                                        from openal import oalOpen
                                        cr_src = oalOpen(cr_path)
                                        if cr_src is not None:
                                            cr_src.play()
                                    except Exception:
                                        pass
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
                sfx_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "SELECT3-1.wav")
                if os.path.exists(sfx_path):
                    # Si la música de fondo está con openal, usar openal para el SFX
                    if self.bg_audio_source is not None:
                        try:
                            from openal import oalOpen
                            sfx_src = oalOpen(sfx_path)
                            if sfx_src is not None:
                                sfx_src.play()
                        except Exception:
                            pass
                    else:
                        # Si estamos en Windows y NO estamos usando winsound para el bg, usar winsound para el SFX
                        if sys.platform.startswith("win") and not self.winsound_used:
                            try:
                                import winsound
                                winsound.PlaySound(sfx_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                            except Exception:
                                # Intentar openal como alternativa
                                try:
                                    from openal import oalOpen
                                    sfx_src = oalOpen(sfx_path)
                                    if sfx_src is not None:
                                        sfx_src.play()
                                except Exception:
                                    pass
                        else:
                            # En otros casos, intentar openal (para no interrumpir winsound de fondo)
                            try:
                                from openal import oalOpen
                                sfx_src = oalOpen(sfx_path)
                                if sfx_src is not None:
                                    sfx_src.play()
                            except Exception:
                                pass
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