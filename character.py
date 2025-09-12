import random
from rich.console import Console


class Personaje:
    def __init__(self, nombre, clase=None, nivel=1):
        self.nombre = nombre or "Aventurero"
        self.nivel = nivel or 1
        self.clase = (clase or "explorador").lower()
        self.tiene_piedra = False
        self.decisiones_desde_ultimo_combate = 0
        self.combates_ganados = 0

        stats = {
            'guerrero': {'salud': 120, 'danio': 15},
            'mago': {'salud': 70, 'danio': 22},
            'explorador': {'salud': 90, 'danio': 12},
            'ladron': {'salud': 85, 'danio': 14},
        }
        base = stats.get(self.clase, {'salud': 80, 'danio': 10})
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
        self.poder_usos = 2
        self.monedas = 10
        self.amuleto_vigor = False
        self.descansos = 0

    def restaurar(self):
        self.salud = self.salud_max
        self.poder_usos = 2
        self.tiene_piedra = False
        self.monedas = 10
        self.amuleto_vigor = False
        self.descansos = 0
        self.decisiones_desde_ultimo_combate = 0
        self.combates_ganados = 0


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


def generar_enemigo(etapa: int):
    catalogo = {
        1: ("Lobo Sombrío", 70, 14, {"sangrado": 0.25}),
        2: ("Espectro del Bosque", 90, 16, {"drain": 0.3}),
        3: ("Guardiana Corrompida", 120, 20, {"stun": 0.2}),
    }
    nombre, base_salud, base_danio, habilidades = catalogo.get(etapa, catalogo[3])
    e = Enemigo(nombre, base_salud, base_danio)
    e.habilidades = habilidades
    return e


def abrir_cofre(jugador, console):
    if jugador is None:
        return
    from audio_manager import play_effect
    import os
    chest_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "CHEST-1.wav")
    play_effect(chest_path)
    tipo = random.choice(["monedas", "curacion"])
    if tipo == "monedas":
        cantidad = random.randint(5, 10)
        jugador.monedas += cantidad
        console.print(f"[yellow]Encuentras un cofre y obtienes {cantidad} monedas. Total: {jugador.monedas}[/]")
    else:
        if jugador.salud >= jugador.salud_max:
            jugador.monedas += 1
            console.print("[dim]El cofre emanaba energía curativa pero estabas al máximo. Obtienes 1 moneda.[/]")
        else:
            curar = random.randint(10, 20)
            antes = jugador.salud
            jugador.salud = min(jugador.salud_max, jugador.salud + curar)
            console.print(f"[green]La luz del cofre te cura. Salud {antes} -> {jugador.salud} (+{jugador.salud-antes}).[/]")


def posible_cofre_aleatorio(juego):
    try:
        if random.random() < 0.15:
            abrir_cofre(juego.jugador, juego.console)
    except Exception:
        pass