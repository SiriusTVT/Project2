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
    historia = [
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

    for parte in historia:
        typewriter(parte, delay=0.03, console=console, style="bold green")
        # pequeña pausa entre párrafos
        time.sleep(0.6)

    # Al final del diálogo introductorio, preguntar si el jugador está listo.
    try:
        respuesta = input("¿Estás listo para la aventura? (s/n): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print("Entrada interrumpida. Saliendo...", style="bold red")
        sys.exit(0)

    # considerar cualquier respuesta que empiece por 's' como afirmativa (si/sí)
    if not respuesta or not respuesta.startswith('s'):
        console.print("No estás listo para la aventura. Hasta la próxima.", style="yellow")
        sys.exit(0)

    console.print("¡Perfecto! La aventura comienza...", style="bold magenta")
    # pedir datos del aventurero
    try:
        nombre = input("Introduce el nombre de tu aventurero: ").strip()
    except (KeyboardInterrupt, EOFError):
        console.print("Entrada interrumpida. Saliendo...", style="bold red")
        sys.exit(0)

    if not nombre:
        nombre = "Aventurero"

    try:
        clase = input("Elige una clase (guerrero/mago/explorador/ladron): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        console.print("Entrada interrumpida. Saliendo...", style="bold red")
        sys.exit(0)

    # crear personaje y mostrar estadísticas
    pj = Personaje(nombre, clase)
    console.print("\n— Estadísticas del aventurero —", style="bold white")
    pj.saludar()


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

if __name__ == "__main__":
    main()