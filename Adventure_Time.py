from rich.console import Console
import time
import sys

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

    def saludar(self):
        print(f"¡Hola! Soy {self.nombre}, clase {self.clase.title()}, nivel {self.nivel}.")
        print(f"Salud: {self.salud}  -  Daño: {self.danio}")



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
    pj.saludar()

    # crear escenas y lanzar el juego
    escenas = crear_escenas()
    juego = Juego(pj, escenas, "inicio")
    juego.run()


def typewriter(text, delay=0.03, console=None, style=None):
    """Imprime `text` carácter por carácter para simular que alguien lo escribe.

    Args:
        text (str): cadena a imprimir.
        delay (float): segundos entre cada carácter.
        console (rich.console.Console|None): consola para imprimir (si no se pasa, se crea una nueva).
        style (str|None): estilo para pasar a console.print.
    """
    if console is None:
        console = Console()
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
    for parte in get_intro_lines():
        typewriter(parte, delay=0.03, console=console, style="bold green")
        time.sleep(0.45)

    # preguntar si el jugador está listo
    try:
        respuesta = input("¿Estás listo para la aventura? (s/n): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print("Entrada interrumpida. Saliendo...", style="bold red")
        return None

    if not respuesta or not respuesta.startswith('s'):
        console.print("No estás listo para la aventura. Hasta la próxima.", style="yellow")
        return None

    console.print("¡Perfecto! La aventura comienza...", style="bold magenta")

    # pedir datos del aventurero
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
        return None

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

    def run(self):
        self.console.print("[bold magenta]¡Bienvenido a Adventure Time versión texto![/]")

        while True:
            escena = self.escenas[self.escena_actual]

            # Acción especial de la escena (si tiene)
            if escena.accion:
                escena.accion(self.jugador)

            escena.mostrar(self.console)
            eleccion = input("\n¿Qué decides hacer?: ")
            siguiente = escena.elegir(eleccion)

            if not siguiente:
                self.console.print("[red]Opción no válida[/]")
                continue

            # Si la escena es un final, terminar
            if siguiente.startswith("final"):
                self.console.print("\n[bold red]--- FIN DEL JUEGO ---[/]\n")
                self.escenas[siguiente].mostrar(self.console)
                break

            self.escena_actual = siguiente


def crear_escenas():
    intro_text = "\n".join(get_intro_lines())
    return {
        "inicio": Escena(
            "Inicio Juego",
            "Toma tu primera decision",
            {"Explorar el sendero a la izquierda": "izquierda",
             "Avanzar hacia el río a la derecha": "rio"},
            sonido="viento+grillos"
        ),

        "izquierda": Escena(
            "Árbol con marcas",
            "Llegas a un árbol con marcas extrañas en la corteza. El ambiente se siente más denso.",
            {"Tocar las marcas": "cabaña",
             "Ignorarlas y seguir adelante": "cabaña"},
            sonido="crujido ramas"
        ),

        "rio": Escena(
            "Río caudaloso",
            "Encuentras un río caudaloso que fluye con fuerza.",
            {"Cruzar el río": "cabaña",
             "Caminar paralelo al río": "cabaña"},
            sonido="agua fuerte"
        ),

        "cabaña": Escena(
            "Cabaña abandonada",
            "Llegas a una pequeña cabaña abandonada. La puerta de madera se mueve con el viento.",
            {"Entrar a la cabaña": "cofre",
             "Rodearla y seguir el camino": "rugido"},
            sonido="puerta+lechuza"
        ),

        "cofre": Escena(
            "El cofre misterioso",
            "Dentro de la cabaña hay un cofre cerrado.",
            {"Abrir el cofre": "mapa",
             "Buscar pistas en el interior": "rugido"},
            sonido="viento rendijas"
        ),

        "mapa": Escena(
            "Mapa secreto",
            "Encuentras un mapa con la ubicación de un santuario escondido.",
            {"Seguir el mapa": "encrucijada"},
            sonido="papel",
            accion=lambda jugador: setattr(jugador, "tiene_piedra", True)
        ),

        "rugido": Escena(
            "El rugido lejano",
            "Sales de la cabaña y escuchas un rugido grave a lo lejos.",
            {"Seguir el rugido": "encrucijada"},
            sonido="rugido"
        ),

        "encrucijada": Escena(
            "La encrucijada",
            "Siguiendo tu camino llegas a una encrucijada. El viento sopla fuerte y las hojas crujen bajo tus pies.",
            {"Ir hacia la montaña": "montaña",
             "Ir hacia la cueva iluminada": "cueva"},
            sonido="viento hojas"
        ),

        "montaña": Escena(
            "El altar en la montaña",
            "Escalas entre rocas y descubres un altar antiguo. Sientes que aquí puedes colocar la piedra mágica.",
            {"Colocar la piedra": "final_heroico",
             "No colocar la piedra": "final_oscuro"},
            sonido="eco viento"
        ),

        "cueva": Escena(
            "La cueva iluminada",
            "Encuentras a una criatura guardiana que te habla con voz grave.\nTe pregunta si deseas continuar tu viaje.",
            {"Aceptar la oferta del guardián": "final_neutral",
             "Rechazar y salir corriendo": "final_oscuro"},
            sonido="respiración+eco"
        ),

        # finales
        "final_heroico": Escena(
            "Final Heroico",
            "Colocas la piedra en el altar. El bosque se ilumina y la magia oscura desaparece.\n¡Has salvado al bosque!",
            {},
            sonido="música triunfal"
        ),

        "final_oscuro": Escena(
            "Final Oscuro",
            "Decides no usar la piedra. La oscuridad crece y quedas atrapado para siempre...",
            {},
            sonido="truenos+risas"
        ),

        "final_neutral": Escena(
            "Final Neutral",
            "Aceptas la oferta del guardián y te conviertes en el nuevo protector del bosque.",
            {},
            sonido="voces místicas"
        ),
    }

if __name__ == "__main__":
    main()