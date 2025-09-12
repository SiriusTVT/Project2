from rich.console import Console
import random, os, sys, time
import time
import sys
import os

# velocidad por defecto para el efecto de "typewriter" (segundos por carácter)
# se puede ajustar con la función `seleccionar_velocidad`
TEXT_SPEED = 0.03

# Referencia global para música de combate para poder detenerla inmediatamente al derrotar al jugador
FIGHT_AUDIO_REF = {"src": None, "winsound": False}
# Referencia global para música de aventura para poder detenerla al entrar a tiendas
BG_AUDIO_REF = {"src": None, "winsound": False}
# Referencia global a la instancia del juego para acceder a bg_audio_source
JUEGO_REF = None
REST_SENTINEL = "__DESCANSO_DYNAMIC__"
# Referencias para audio de derrota (FAILBATTLE / LOSE)
DEFEAT_AUDIO = {"sources": [], "winsound": False}

# Conjuntos de terreno para sonido de pasos
TERRAIN_FOREST = {"inicio", "izquierda", "rio", "rugido", "encrucijada"}
TERRAIN_SOLID = {"cabaña", "cofre", "mapa", "pelea", "combate", "montaña", "cueva", "final_heroico", "final_oscuro", "final_neutral", "sendero_profundo", "bosque_bruma", "claro_corrupto", "claro_final"}

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
        """Inicializa el personaje con estadísticas base, poder, economía y descansos."""
        self.nombre = nombre or "Aventurero"
        self.nivel = nivel or 1
        self.clase = (clase or "explorador").lower()
        self.tiene_piedra = False
        # Contadores para nuevas reglas
        self.decisiones_desde_ultimo_combate = 0  # Debe alcanzar >=3 para permitir otro combate
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

        # Economía
        self.monedas = 10
        self.amuleto_vigor = False

        # Conteo de descansos disponibles (máximo 3)
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

# ------------------- Cofres ------------------- #
def abrir_cofre(jugador, console):
    """Otorga el contenido de un cofre: monedas (5-10) o curación (10-20).
    Si el jugador está al máximo y sale curación, recibe 1 moneda en su lugar."""
    if jugador is None:
        return
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
    """15% de probabilidad de disparar un cofre aleatorio en exploración."""
    try:
        if random.random() < 0.15:
            abrir_cofre(juego.jugador, juego.console)
    except Exception:
        pass

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

# ------------------- NUEVAS UTILIDADES DE DIFICULTAD / ENEMIGOS ------------------- #
def generar_enemigo(etapa:int):
    """Genera un enemigo según la etapa de dificultad (1..N)."""
    catalogo = {
        1: ("Lobo Sombrío", 70, 14, {"sangrado":0.25}),
        2: ("Espectro del Bosque", 90, 16, {"drain":0.3}),
        3: ("Guardiana Corrompida", 120, 20, {"stun":0.2}),
    }
    nombre, base_salud, base_danio, habilidades = catalogo.get(etapa, catalogo[3])
    e = Enemigo(nombre, base_salud, base_danio)
    e.habilidades = habilidades
    return e

def handle_derrota(jugador):
    """Gestiona audio y flujo cuando el jugador es derrotado en cualquier combate.

    Devuelve 'reiniciar' si el usuario desea volver a empezar o 'final_oscuro' si no.
    """
    console = Console()
    console.print("\n[bold red]Has sido derrotado...[/]")
    # Detener música de combate previa
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
        FIGHT_AUDIO_REF["src"] = None
        FIGHT_AUDIO_REF["winsound"] = False
    except Exception:
        pass
    # Reproducir audios de derrota (FAILBATTLE + LOSE) simultáneamente si es posible
    base_dir = os.path.dirname(__file__)
    fail_path = os.path.join(base_dir, "Music", "FAILBATTLE-1.wav")
    lose_path = os.path.join(base_dir, "Sound Effects", "LOSE-1.wav")
    played_openal = False
    try:
        from openal import oalOpen
        fuentes = []
        for p in (fail_path, lose_path):
            if os.path.exists(p):
                try:
                    s = oalOpen(p)
                    if s is not None:
                        if p.endswith("FAILBATTLE-1.wav"):
                            try:
                                s.set_gain(0.4)  # un poco más bajo
                            except Exception:
                                pass
                        s.play()
                        fuentes.append(s)
                except Exception:
                    pass
        if fuentes:
            played_openal = True
            DEFEAT_AUDIO["sources"] = fuentes
            DEFEAT_AUDIO["winsound"] = False
    except Exception:
        pass
    if not played_openal:
        # Fallback secuencial
        play_effect(fail_path)
        play_effect(lose_path)
        if sys.platform.startswith("win"):
            DEFEAT_AUDIO["sources"] = []
            DEFEAT_AUDIO["winsound"] = True
    # Preguntar reinicio
    while True:
        try:
            resp = input("¿Quieres intentarlo de nuevo desde el inicio? (s/n): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            resp = 'n'
        if resp.startswith('s'):
            # detener audios derrota
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
            if hasattr(jugador, 'restaurar'):
                jugador.restaurar()
            return "reiniciar"
        if resp.startswith('n') or resp == '':
            return "final_oscuro"
        console.print("[yellow]Opción no válida. Responde s o n.[/]")

def combate_personalizado(etapa:int, proxima_escena="sendero_profundo"):
    """Devuelve una función de acción para una Escena que ejecuta un combate escalado."""
    def _accion(jugador):
        enemigo = generar_enemigo(etapa)
        console = Console()
        console.print(f"\n[bold red]¡{enemigo.nombre} aparece![/]")
        if not hasattr(jugador, "poder_usos"):
            jugador.poder_usos = 2
        defensa = False
        heals_used = 0
        defense_used = 0
        skip_enemy_attack = False
        turno_cont = 0
        while jugador.salud > 0 and enemigo.salud > 0:
            turno_cont += 1
            console.print(f"\nTu salud: [green]{jugador.salud}[/] / {jugador.salud_max}")
            enemigo.mostrar(console)
            console.print("\nElige tu acción:")
            console.print("1. Atacar")
            console.print(f"2. Poder especial ({jugador.poder}) [{getattr(jugador,'poder_usos',0)} usos]")
            console.print(f"3. Defender (contraataque 5 daño) [{2-defense_used} usos]")
            console.print(f"4. Curarse (+15) [{3-heals_used} usos]")
            accion = input("Acción (1-4): ").strip()
            if accion == "1":
                play_effect(os.path.join(os.path.dirname(__file__), "Player Effects", "SWORD-1.wav"))
                danio = jugador.danio
                if hasattr(enemigo, 'habilidades') and 'stun' in enemigo.habilidades and turno_cont % 4 == 0:
                    console.print("[dim]El aura corrupta reduce tu precisión (-20% daño este turno).[/]")
                    danio = int(danio*0.8)
                enemigo.salud -= danio
                console.print(f"Golpeas e infliges [yellow]{danio}[/] de daño.")
            elif accion == "2":
                if getattr(jugador,'poder_usos',0) > 0:
                    play_effect(os.path.join(os.path.dirname(__file__), "Player Effects", "SWORD-1.wav"))
                    danio = jugador.danio + 10
                    enemigo.salud -= danio
                    jugador.poder_usos -= 1
                    console.print(f"Usas tu poder especial y haces [yellow]{danio}[/] de daño!")
                else:
                    console.print("[dim]No te quedan usos del poder.[/]")
                    continue
            elif accion == "3":
                if defense_used >= 2:
                    console.print("[yellow]Ya no puedes defender más en este combate.[/]")
                    continue
                defense_used += 1
                defensa = True
                skip_enemy_attack = True  # niega el ataque enemigo
                play_effect(os.path.join(os.path.dirname(__file__), "Player Effects", "SHIELD-1.wav"))
                enemigo.salud -= 5
                console.print("[green]Bloqueas todo el daño y contraatacas por [yellow]5[/].")
            elif accion == "4":
                if heals_used >= 3:
                    console.print("[yellow]No puedes curarte más en este combate.[/]")
                    continue
                deficit = jugador.salud_max - jugador.salud
                if deficit <= 0:
                    console.print("[dim]Ya estás al máximo.[/]")
                    continue
                curar = min(15, deficit)
                jugador.salud += curar
                heals_used += 1
                # Ataque oportunista del enemigo (1-10) y se salta ataque normal este turno
                dano_rebote = random.randint(1,10)
                jugador.salud = max(1, jugador.salud - dano_rebote)
                skip_enemy_attack = True
                console.print(f"[green]Te curas {curar}. [/][red]El enemigo aprovecha y te hiere (-{dano_rebote}). Salud actual: {jugador.salud}[/]")
            else:
                console.print("[red]Acción no válida[/]")
                continue
            # turno enemigo
            if enemigo.salud > 0 and not skip_enemy_attack:
                base = enemigo.danio
                tipo = random.choice(["normal","fuerte"]) if etapa>1 else "normal"
                if tipo == "fuerte":
                    base += 5
                if defensa:
                    base = 0
                    defensa = False
                # habilidades
                if hasattr(enemigo,'habilidades'):
                    hab = enemigo.habilidades
                    if 'sangrado' in hab and random.random() < hab['sangrado']:
                        extra = 4
                        console.print("[red]El lobo te desgarra y causa sangrado (+4).[/]")
                        base += extra
                    if 'drain' in hab and random.random() < hab['drain']:
                        dr = 6
                        console.print("[magenta]El espectro absorbe tu energía (+6).[/]")
                        enemigo.salud = min(enemigo.salud+dr, enemigo.salud_max)
                    if 'stun' in hab and random.random() < hab['stun']:
                        console.print("[bold red]La guardiana te aturde: pierdes el próximo 10% de daño.")
                        jugador.danio = max(1, int(jugador.danio*0.9))
                if base>0:
                    jugador.salud -= base
                    console.print(f"Recibes [red]{base}[/] de daño.")
                else:
                    console.print("[green]Bloqueas todo el ataque enemigo.[/]")
            skip_enemy_attack = False
            time.sleep(0.4)
        if jugador.salud>0:
            console.print(f"\n[bold green]¡Has derrotado a {enemigo.nombre}![/]")
            play_effect(os.path.join(os.path.dirname(__file__), "Sound Effects", "WINBATTLE-1.wav"))
            # escalar progreso
            jugador.nivel_progreso = getattr(jugador,'nivel_progreso',0)+1
            # Recompensa monetaria (nueva regla 5-15)
            recompensa = random.randint(5,15)
            jugador.monedas += recompensa
            console.print(f"[yellow]Obtienes {recompensa} monedas. Total: {jugador.monedas}[/]")
            jugador.combates_ganados += 1
            jugador.decisiones_desde_ultimo_combate = 0
            return proxima_escena
        else:
            return handle_derrota(jugador)
    return _accion

# ------------------- LABERINTO DINÁMICO ------------------- #
def generar_laberinto(tam):
    import random
    # Representación simple: 0 pared, 1 camino
    ancho = alto = tam
    lab = [[0]*ancho for _ in range(alto)]
    # Carvar con DFS
    dirs = [(1,0),(-1,0),(0,1),(0,-1)]
    def carve(x,y):
        lab[y][x]=1
        random.shuffle(dirs)
        for dx,dy in dirs:
            nx,ny = x+dx*2, y+dy*2
            if 0<=nx<ancho and 0<=ny<alto and lab[ny][nx]==0:
                lab[y+dy][x+dx]=1
                carve(nx,ny)
    carve(0,0)
    lab[alto-1][ancho-1]=1
    return lab

def laberinto_action(jugador):
    console = Console()
    dificultad = getattr(jugador,'nivel_progreso',0)
    tam = 7 if dificultad<2 else (9 if dificultad<4 else 11)
    console.print(f"[bold cyan]Entras a un laberinto místico (tamaño {tam}x{tam}). Encuentra la salida (X). Usa WASD.[/]")
    lab = generar_laberinto(tam)
    px,py = 0,0
    ex,ey = tam-1,tam-1
    pasos_max = tam*tam*2
    pasos = 0
    trampa_intervalo = max(6, tam//2)
    while (px,py)!=(ex,ey) and pasos<pasos_max and jugador.salud>0:
        # vista parcial 5x5
        vista=""
        for y in range(max(0,py-2), min(tam,py+3)):
            fila=""
            for x in range(max(0,px-2), min(tam,px+3)):
                if (x,y)==(px,py): fila+="P"
                elif (x,y)==(ex,ey): fila+="X"
                else: fila += "." if lab[y][x]==1 else "#"
            vista+=fila+"\n"
        console.print(f"[green]{vista}[/]")
        mov = input("Movimiento (w/a/s/d, q salir): ").strip().lower()
        if mov=='q':
            return "final_oscuro"
        dx=dy=0
        if mov=='w': dy=-1
        elif mov=='s': dy=1
        elif mov=='a': dx=-1
        elif mov=='d': dx=1
        else:
            console.print("[dim]Entrada no válida[/]")
            continue
        nx,ny = px+dx, py+dy
        if 0<=nx<tam and 0<=ny<tam and lab[ny][nx]==1:
            px,py = nx,ny
            pasos+=1
            # trampa periódica
            if pasos % trampa_intervalo == 0 and pasos>0:
                import random
                if random.random()<0.5:
                    danio = 5 + dificultad*3
                    jugador.salud -= danio
                    console.print(f"[red]Una trampa oculta te hiere (-{danio}). Salud: {jugador.salud}[/]")
        else:
            console.print("[yellow]Golpeas una pared.[/]")
    if (px,py)==(ex,ey) and jugador.salud>0:
        console.print("[bold green]¡Escapas del laberinto! Sientes que has crecido en experiencia." )
        jugador.nivel_progreso = getattr(jugador,'nivel_progreso',0)+1
        # decidir hacia dónde conduce
        return "montaña" if jugador.tiene_piedra else "cueva"
    console.print("[bold red]Fracaso en el laberinto...[/]")
    return "final_oscuro"

def combate(jugador):
    console = Console()
    enemigo = Enemigo()
    console.print("\n[bold red]¡Una bestia sombría aparece![/]")
    defensa = False
    heals_used = 0
    defense_used = 0
    skip_enemy_attack = False
    if not hasattr(jugador, "poder_usos"):
        jugador.poder_usos = 2
    while jugador.salud > 0 and enemigo.salud > 0:
        console.print(f"\nTu salud: [green]{jugador.salud}[/] / {jugador.salud_max}")
        enemigo.mostrar(console)
        console.print("\nElige tu acción:")
        console.print("1. Atacar")
        console.print(f"2. Usar poder especial ({jugador.poder}) [{jugador.poder_usos} usos restantes]")
        console.print(f"3. Defender (contraataque 5 daño) [{2-defense_used} usos]")
        console.print(f"4. Curarse (+15 salud) [{3-heals_used} usos]")
        accion = input("Acción (1-4): ").strip()
        if accion == "1":
            play_effect(os.path.join(os.path.dirname(__file__), "Player Effects", "SWORD-1.wav"))
            danio = jugador.danio
            console.print(f"Atacas y haces [yellow]{danio}[/] de daño.")
            enemigo.salud -= danio
        elif accion == "2":
            if jugador.poder_usos > 0:
                play_effect(os.path.join(os.path.dirname(__file__), "Player Effects", "SWORD-1.wav"))
                danio = jugador.danio + 10
                console.print(f"Usas tu poder especial '{jugador.poder}' y haces [yellow]{danio}[/] de daño!")
                enemigo.salud -= danio
                jugador.poder_usos -= 1
            else:
                console.print("[dim]Ya no puedes usar tu poder especial.[/]")
        elif accion == "3":
            if defense_used >= 2:
                console.print("[yellow]Ya no puedes defender más en este combate.[/]")
                continue
            defense_used += 1
            defensa = True
            skip_enemy_attack = True
            play_effect(os.path.join(os.path.dirname(__file__), "Player Effects", "SHIELD-1.wav"))
            enemigo.salud -= 5
            console.print("[green]Bloqueas todo y contraatacas infligiendo 5 de daño![/]")
        elif accion == "4":
            if heals_used >= 3:
                console.print("[yellow]No puedes curarte más en este combate.[/]")
                continue
            deficit = jugador.salud_max - jugador.salud
            if deficit <= 0:
                console.print("[dim]Tu salud ya está completa.[/]")
                continue
            curar = min(15, deficit)
            jugador.salud += curar
            heals_used += 1
            dano_rebote = random.randint(1,10)
            jugador.salud = max(1, jugador.salud - dano_rebote)
            skip_enemy_attack = True
            console.print(f"[green]Te curas {curar}. [/][red]El enemigo reacciona y te hiere (-{dano_rebote}). Salud: {jugador.salud}[/]")
        else:
            console.print("[red]Acción no válida.[/]")
            continue
        if enemigo.salud > 0 and not skip_enemy_attack:
            ataque = random.choice(["normal", "fuerte"])
            if ataque == "normal":
                danio_enemigo = enemigo.danio
                mensaje = "La bestia te ataca."
            else:
                danio_enemigo = enemigo.danio + 5
                mensaje = "La bestia lanza un ataque feroz!"
            if defensa:
                danio_enemigo = 0
                defensa = False
                console.print("[green]Bloqueas el ataque completamente![/]")
            if danio_enemigo>0:
                jugador.salud -= danio_enemigo
                console.print(f"{mensaje} Recibes [red]{danio_enemigo}[/] de daño.")
        skip_enemy_attack = False
        time.sleep(0.5)
    if jugador.salud > 0:
        console.print("\n[bold green]¡Has vencido a la bestia![/]")
        play_effect(os.path.join(os.path.dirname(__file__), "Sound Effects", "WINBATTLE-1.wav"))
        jugador.nivel_progreso = max(getattr(jugador, 'nivel_progreso', 0), 1)
        # Recompensa monetaria (5-15)
        recompensa = random.randint(5,15)
        jugador.monedas += recompensa
        console.print(f"[yellow]Obtienes {recompensa} monedas. Total: {jugador.monedas}[/]")
        jugador.combates_ganados += 1
        jugador.decisiones_desde_ultimo_combate = 0
    return "respiro_bosque"
    return handle_derrota(jugador)

# ------------------- TIENDAS / ECONOMIA ------------------- #
def tienda_factory(retorno:str):
    """Crea una acción de escena que abre una tienda y retorna a `retorno`."""
    def _tienda(j):
        console = Console()
        console.print("\n[bold cyan]Tienda del viajero[/]")
        # Detener música de aventura temporalmente y reproducir música de tienda
        store_path = os.path.join(os.path.dirname(__file__), "Music", "STORE-1.wav")
        adventure_path = os.path.join(os.path.dirname(__file__), "Music", "ADVENTURE-1.wav")
        store_src = None
        used_winsound_store = False
        # Detener explícitamente música de aventura si está sonando
        try:
            if BG_AUDIO_REF.get("src") is not None:
                try:
                    BG_AUDIO_REF["src"].stop()
                except Exception:
                    pass
                BG_AUDIO_REF["src"] = None
            # Intentar siempre detener winsound aunque la bandera no esté marcada (seguro idempotente)
            if sys.platform.startswith("win"):
                try:
                    import winsound
                    winsound.PlaySound(None, 0)
                except Exception:
                    pass
            BG_AUDIO_REF["winsound"] = False
            # Barrido adicional: si existe algún objeto global con atributo bg_audio_source, detenerlo
            try:
                for _name, _obj in globals().items():
                    if hasattr(_obj, 'bg_audio_source'):
                        src = getattr(_obj, 'bg_audio_source')
                        try:
                            if src is not None:
                                src.stop()
                        except Exception:
                            pass
                        try:
                            setattr(_obj, 'bg_audio_source', None)
                        except Exception:
                            pass
                    if hasattr(_obj, 'winsound_used') and getattr(_obj, 'winsound_used'):
                        # limpiar bandera para que no se reanude automáticamente en lógica futura
                        try:
                            setattr(_obj, 'winsound_used', False)
                        except Exception:
                            pass
                # Intento directo usando JUEGO_REF (más robusto)
                try:
                    if JUEGO_REF is not None and hasattr(JUEGO_REF, 'bg_audio_source'):
                        src = getattr(JUEGO_REF, 'bg_audio_source')
                        if src is not None:
                            try: src.stop()
                            except Exception: pass
                            try: setattr(JUEGO_REF, 'bg_audio_source', None)
                            except Exception: pass
                        if hasattr(JUEGO_REF, 'winsound_used') and getattr(JUEGO_REF, 'winsound_used'):
                            setattr(JUEGO_REF, 'winsound_used', False)
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass
        # parar efectos cortos en curso
        try:
            if LAST_SFX.get("src") is not None:
                try: LAST_SFX["src"].stop()
                except Exception: pass
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
        # detener música aventura
        try:
            from openal import oalOpen
            if 'juego' in globals():
                pass
        except Exception:
            pass
        try:
            # si hay fuente openal guardada (referencia global posible vía bg_audio_source en Juego)
            # No tenemos acceso directo a la instancia Juego aquí; se asume música de aventura se detiene antes de llamar acción de escena si es necesario.
            # Intentar openal primero
            from openal import oalOpen
            if os.path.exists(store_path):
                try:
                    store_src = oalOpen(store_path)
                    if store_src is not None:
                        try:
                            store_src.set_gain(0.25)
                        except Exception:
                            try: store_src.gain = 0.25
                            except Exception: pass
                        store_src.play()
                except Exception:
                    store_src = None
        except Exception:
            store_src = None
        if store_src is None and sys.platform.startswith("win") and os.path.exists(store_path):
            try:
                import winsound
                winsound.PlaySound(store_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                used_winsound_store = True
            except Exception:
                pass
        while True:
            console.print(f"Monedas: [yellow]{j.monedas}[/] | Salud: [green]{j.salud}/{j.salud_max}[/] | Daño: [red]{j.danio}[/]")
            console.print("Elige un artículo:")
            console.print("1. Poción pequeña (+20 salud) - 5 monedas")
            console.print("2. Poción grande (salud completa) - 9 monedas")
            console.print("3. Afilar arma (+3 daño) - 8 monedas")
            console.print("4. Amuleto de vigor (+10 salud máx, una vez) - 10 monedas")
            console.print("5. Restaurar poderes especiales (2 usos) - 4 monedas")
            console.print("6. Salir de la tienda")
            elec = input("Opción (1-6): ").strip()
            # Sonido de selección para cualquier opción ingresada (válida o salida)
            try:
                sel_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "SELECT3-1.wav")
                if os.path.exists(sel_path):
                    play_effect(sel_path)
            except Exception:
                pass
            if elec == '1':
                if j.monedas >=5:
                    j.monedas -=5
                    j.salud = min(j.salud_max, j.salud+20)
                    console.print(f"[green]Te curas. Salud: {j.salud}/{j.salud_max} (Monedas: {j.monedas})[/]")
                else:
                    console.print("[red]Monedas insuficientes.[/]")
            elif elec == '2':
                if j.monedas >=9:
                    j.monedas -=9
                    j.salud = j.salud_max
                    console.print(f"[green]Salud restaurada completamente. (Monedas: {j.monedas})[/]")
                else:
                    console.print("[red]Monedas insuficientes.[/]")
            elif elec == '3':
                if j.monedas >=8:
                    j.monedas -=8
                    j.danio +=3
                    console.print(f"[yellow]Tu daño aumenta a {j.danio}. (Monedas: {j.monedas})[/]")
                else:
                    console.print("[red]Monedas insuficientes.[/]")
            elif elec == '4':
                if j.amuleto_vigor:
                    console.print("[dim]Ya posees el amuleto.[/]")
                elif j.monedas >=10:
                    j.monedas -=10
                    j.salud_max +=10
                    j.salud = min(j.salud_max, j.salud+10)
                    j.amuleto_vigor = True
                    console.print(f"[green]Amuleto adquirido. Salud máx: {j.salud_max}. (Monedas: {j.monedas})[/]")
                else:
                    console.print("[red]Monedas insuficientes.[/]")
            elif elec == '5':
                if j.monedas >=4:
                    j.monedas -=4
                    j.poder_usos = 2
                    console.print(f"[magenta]Poderes restaurados (2 usos). (Monedas: {j.monedas})[/]")
                else:
                    console.print("[red]Monedas insuficientes.[/]")
            elif elec == '6' or elec == '':
                console.print("[dim]Abandonas la tienda.[/]")
                # detener música tienda
                try:
                    if store_src is not None:
                        try: store_src.stop()
                        except Exception: pass
                    if used_winsound_store and sys.platform.startswith("win"):
                        try:
                            import winsound
                            winsound.PlaySound(None, 0)
                        except Exception:
                            pass
                except Exception:
                    pass
                # reanudar aventura
                try:
                    if os.path.exists(adventure_path):
                        # intentar openal
                        try:
                            from openal import oalOpen
                            adv_src = oalOpen(adventure_path)
                            if adv_src is not None:
                                try:
                                    adv_src.set_gain(0.2)
                                except Exception:
                                    try: adv_src.gain = 0.2
                                    except Exception: pass
                                adv_src.play()
                                try:
                                    BG_AUDIO_REF["src"] = adv_src
                                    BG_AUDIO_REF["winsound"] = False
                                except Exception:
                                    pass
                        except Exception:
                            if sys.platform.startswith("win"):
                                try:
                                    import winsound
                                    winsound.PlaySound(adventure_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                                    try:
                                        BG_AUDIO_REF["src"] = None
                                        BG_AUDIO_REF["winsound"] = True
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                except Exception:
                    pass
                return retorno
            else:
                console.print("[red]Opción no válida.[/]")
    return _tienda

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
    console.print(f"Monedas: [yellow]{pj.monedas}[/]")

    # crear escenas y lanzar el juego
    escenas = crear_escenas()
    juego = Juego(pj, escenas, "inicio")
    try:
        global JUEGO_REF
        JUEGO_REF = juego
    except Exception:
        pass

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
                # guardar referencia para detener al final
                juego.bg_audio_source = bg_src
                juego.oal_quit = oalQuit
                try:
                    BG_AUDIO_REF["src"] = bg_src
                    BG_AUDIO_REF["winsound"] = False
                except Exception:
                    pass
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
                    try:
                        BG_AUDIO_REF["src"] = None
                        BG_AUDIO_REF["winsound"] = True
                    except Exception:
                        pass
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
        # referencia para sonido ambiente de cueva
        self.cave_src = None
        self.cave_winsound = False
        # referencias para música de combate
        self.fight_src = None
        self.fight_winsound = False

    def run(self):
        self.console.print("[bold magenta]¡Bienvenido a Adventure Time versión texto![/]")

        while True:
            # Fallback ante escenas faltantes (por ejemplo cofres buenos/malos)
            try:
                escena = self.escenas[self.escena_actual]
            except KeyError:
                # Crear de emergencia escenas de cofre si faltan
                def _fallback_good(next_scene):
                    def _a(j):
                        c = self.console
                        if j.salud < j.salud_max and random.choice([True, False]):
                            heal = random.randint(10,15)
                            antes = j.salud
                            j.salud = min(j.salud_max, j.salud + heal)
                            c.print(f"[green]Energía benevolente: {antes}->{j.salud} (+{j.salud-antes}).[/]")
                        else:
                            if j.salud >= j.salud_max:
                                j.monedas += 1
                                c.print("[dim]No necesitas curación. Obtienes 1 moneda.[/]")
                            gain = random.randint(2,5)
                            j.monedas += gain
                            c.print(f"[yellow]Ganas {gain} monedas. Total: {j.monedas}[/]")
                        return next_scene
                    return _a
                def _fallback_bad(next_scene):
                    def _a(j):
                        c = self.console
                        if random.choice([True, False]):
                            loss = min(j.monedas, random.randint(1,3))
                            j.monedas -= loss
                            c.print(f"[red]Pierdes {loss} monedas. Total: {j.monedas}[/]")
                        else:
                            dmg = random.randint(5,10)
                            j.salud = max(1, j.salud - dmg)
                            c.print(f"[red]Sufres {dmg} de daño. Salud: {j.salud}[/]")
                        return next_scene
                    return _a
                # Registrar faltantes mínimos
                if 'cofre_bosque_bueno' not in self.escenas:
                    self.escenas['cofre_bosque_bueno'] = Escena("Cofre bosque (bueno)", "Emergencia.", {}, accion=_fallback_good("eco_lejano"))
                if 'cofre_bosque_malo' not in self.escenas:
                    self.escenas['cofre_bosque_malo'] = Escena("Cofre bosque (malo)", "Emergencia.", {}, accion=_fallback_bad("eco_lejano"))
                if 'cofre_bruma_bueno' not in self.escenas:
                    self.escenas['cofre_bruma_bueno'] = Escena("Cofre bruma (bueno)", "Emergencia.", {}, accion=_fallback_good("susurro_distante"))
                if 'cofre_bruma_malo' not in self.escenas:
                    self.escenas['cofre_bruma_malo'] = Escena("Cofre bruma (malo)", "Emergencia.", {}, accion=_fallback_bad("susurro_distante"))
                if 'cofre_corrupto_bueno' not in self.escenas:
                    self.escenas['cofre_corrupto_bueno'] = Escena("Cofre corrupto (bueno)", "Emergencia.", {}, accion=_fallback_good("latido_sombra"))
                if 'cofre_corrupto_malo' not in self.escenas:
                    self.escenas['cofre_corrupto_malo'] = Escena("Cofre corrupto (malo)", "Emergencia.", {}, accion=_fallback_bad("latido_sombra"))
                # Reintentar
                escena = self.escenas.get(self.escena_actual)
                if escena is None:
                    self.console.print(f"[red]Escena perdida: {self.escena_actual}. Redirigiendo al sendero profundo.[/]")
                    self.escena_actual = 'sendero_profundo'
                    escena = self.escenas[self.escena_actual]

            # Inyectar opción de descanso dinámica si procede
            try:
                if (not self.escena_actual.startswith("final") and
                    self.escena_actual not in {"combate","combate_lobo","combate_espectro","combate_guardiana"} and
                    not self.escena_actual.startswith("tienda") and
                    getattr(self.jugador, 'descansos', 0) < 3):
                    if "Descansar (+10 salud)" not in escena.opciones:
                        escena.opciones = dict(escena.opciones)
                        escena.opciones["Descansar (+10 salud)"] = REST_SENTINEL
                elif getattr(self.jugador, 'descansos', 0) >= 3 and "Descansar (+10 salud)" in escena.opciones:
                    escena.opciones = {k:v for k,v in escena.opciones.items() if k != "Descansar (+10 salud)"}
            except Exception:
                pass

            # Manejo directo si ya estamos en un final (por ejemplo tras derrota -> final_oscuro)
            if self.escena_actual.startswith("final"):
                self.console.print("\n[bold red]--- FIN DEL JUEGO ---[/]\n")
                escena.mostrar(self.console)
                if self.escena_actual == "final_oscuro":
                    try:
                        input("Presiona Enter para finalizar...")
                    except (KeyboardInterrupt, EOFError):
                        pass
                # Detener audios (reutiliza lógica existente simplificada)
                try:
                    for src_name in ["fight_src","river_src","cave_src","bg_audio_source"]:
                        src = getattr(self, src_name, None)
                        if src is not None:
                            try: src.stop()
                            except Exception: pass
                        setattr(self, src_name, None)
                    if sys.platform.startswith("win"):
                        import winsound
                        winsound.PlaySound(None, 0)
                except Exception:
                    pass
                break

            # Acción especial de la escena (si tiene)
            siguiente_accion = None
            if escena.accion:
                # Si vamos a entrar en combate, cambiar a música de pelea (todas las variantes)
                combate_scenes = {"combate","combate_lobo","combate_espectro","combate_guardiana"}
                was_fight = (self.escena_actual in combate_scenes)
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
                        # detener cualquier música previa (aventura o pelea residual) para evitar solapamiento
                        try:
                            # detener música de pelea previa
                            if self.fight_src is not None:
                                try: self.fight_src.stop()
                                except Exception: pass
                                self.fight_src = None
                            if getattr(self, 'fight_winsound', False) and sys.platform.startswith("win"):
                                try:
                                    import winsound
                                    winsound.PlaySound(None, 0)
                                except Exception:
                                    pass
                                self.fight_winsound = False
                        except Exception:
                            pass
                        try:
                            # detener música de aventura global si existe
                            if 'BG_AUDIO_REF' in globals():
                                if BG_AUDIO_REF.get("src") is not None:
                                    try: BG_AUDIO_REF["src"].stop()
                                    except Exception: pass
                                    BG_AUDIO_REF["src"] = None
                                if BG_AUDIO_REF.get("winsound") and sys.platform.startswith("win"):
                                    try:
                                        import winsound
                                        winsound.PlaySound(None, 0)
                                    except Exception:
                                        pass
                                    BG_AUDIO_REF["winsound"] = False
                        except Exception:
                            pass
                        fight_path = os.path.join(os.path.dirname(__file__), "Music", "FIGHT-1.wav")
                        if os.path.exists(fight_path):
                            played = False
                            # Intentar siempre OpenAL primero
                            try:
                                from openal import oalOpen
                                f_src = oalOpen(fight_path)
                                if f_src is not None:
                                    try:
                                        f_src.set_gain(0.3)
                                    except Exception:
                                        try: f_src.gain = 0.3
                                        except Exception: pass
                                    f_src.play()
                                    self.fight_src = f_src
                                    self.fight_winsound = False
                                    try:
                                        FIGHT_AUDIO_REF["src"] = f_src
                                        FIGHT_AUDIO_REF["winsound"] = False
                                    except Exception:
                                        pass
                                    played = True
                            except Exception:
                                pass
                            # Si OpenAL no funcionó usar winsound si está en Windows
                            if not played and sys.platform.startswith("win"):
                                try:
                                    import winsound
                                    winsound.PlaySound(fight_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                                    self.fight_src = None
                                    self.fight_winsound = True
                                    try:
                                        FIGHT_AUDIO_REF["src"] = None
                                        FIGHT_AUDIO_REF["winsound"] = True
                                    except Exception:
                                        pass
                                    played = True
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
                                # Intentar recrear música de aventura si se perdió (caso tiendas u otros)
                                try:
                                    adv_path = os.path.join(os.path.dirname(__file__), "Music", "ADVENTURE-1.wav")
                                    if os.path.exists(adv_path):
                                        started = False
                                        # Intentar OpenAL primero
                                        try:
                                            from openal import oalOpen
                                            src = oalOpen(adv_path)
                                            if src is not None:
                                                try:
                                                    src.set_gain(0.2)
                                                except Exception:
                                                    try: src.gain = 0.2
                                                    except Exception: pass
                                                src.play()
                                                self.bg_audio_source = src
                                                started = True
                                                try:
                                                    BG_AUDIO_REF["src"] = src
                                                    BG_AUDIO_REF["winsound"] = False
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass
                                        if not started and sys.platform.startswith("win"):
                                            try:
                                                import winsound
                                                winsound.PlaySound(adv_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                                                self.winsound_used = True
                                                try:
                                                    BG_AUDIO_REF["src"] = None
                                                    BG_AUDIO_REF["winsound"] = True
                                                except Exception:
                                                    pass
                                            except Exception:
                                                pass
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
                        if os.path.exists(adv_path):
                            if self.bg_audio_source is not None:
                                try:
                                    self.bg_audio_source.play()
                                except Exception:
                                    pass
                            else:
                                # Intentar crear nueva fuente OpenAL primero
                                started = False
                                try:
                                    from openal import oalOpen
                                    src = oalOpen(adv_path)
                                    if src is not None:
                                        try:
                                            src.set_gain(0.2)
                                        except Exception:
                                            try: src.gain = 0.2
                                            except Exception: pass
                                        src.play()
                                        self.bg_audio_source = src
                                        started = True
                                        try:
                                            BG_AUDIO_REF["src"] = src
                                            BG_AUDIO_REF["winsound"] = False
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                                if not started and sys.platform.startswith("win"):
                                    try:
                                        import winsound
                                        winsound.PlaySound(adv_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                                        self.winsound_used = True
                                        try:
                                            BG_AUDIO_REF["src"] = None
                                            BG_AUDIO_REF["winsound"] = True
                                        except Exception:
                                            pass
                                    except Exception:
                                        pass
                    except Exception:
                        pass
                    # Reiniciar escena al inicio
                    self.escena_actual = "inicio"
                    continue
                self.escena_actual = siguiente_accion
                continue

            escena.mostrar(self.console)
            eleccion = input("\n¿Qué decides hacer?: ")
            destino_tmp = escena.elegir(eleccion)
            if destino_tmp == REST_SENTINEL:
                try:
                    if getattr(self.jugador,'descansos',0) >= 3:
                        self.console.print("[yellow]Ya no puedes descansar más (3/3).[/]")
                    else:
                        if self.jugador.salud >= self.jugador.salud_max:
                            self.console.print("[dim]Tu salud ya está completa. No consumes un descanso.[/]")
                        else:
                            antes = self.jugador.salud
                            self.jugador.salud = min(self.jugador.salud_max, self.jugador.salud + 10)
                            self.jugador.descansos += 1
                            self.console.print(f"[green]Descansas ({self.jugador.descansos}/3). Salud {antes} -> {self.jugador.salud} (+{self.jugador.salud-antes})[/]")
                            if self.jugador.descansos >= 3 and "Descansar (+10 salud)" in escena.opciones:
                                escena.opciones = {k:v for k,v in escena.opciones.items() if k != "Descansar (+10 salud)"}
                except Exception:
                    pass
                continue
            siguiente = destino_tmp

            if not siguiente:
                self.console.print("[red]Opción no válida[/]")
                continue

            # Gating de combate: requerir 3 decisiones previas
            try:
                contador = getattr(self.jugador, 'decisiones_desde_ultimo_combate', 0)
                if str(siguiente).startswith("combate") and contador < 3:
                    self.console.print("[yellow]Aún no estás listo para otro combate. Exploras un poco más...[/]")
                    mapping = {
                        'combate': 'encrucijada',
                        # Evitar bucle: si aún no se puede pelear contra el lobo, enviar a 'eco_lejano' como avance narrativo
                        'combate_lobo': 'eco_lejano',
                        'combate_espectro': 'bosque_bruma',
                        'combate_guardiana': 'claro_corrupto'
                    }
                    siguiente = mapping.get(siguiente, 'encrucijada')
                    contador += 1  # cuenta como decisión
                    setattr(self.jugador, 'decisiones_desde_ultimo_combate', contador)
                elif (not str(siguiente).startswith("combate")) and (not str(siguiente).startswith("final")):
                    contador += 1
                    setattr(self.jugador, 'decisiones_desde_ultimo_combate', contador)
            except Exception:
                pass

            # (Cofres aleatorios desactivados según nueva especificación)

            # Determinar texto exacto de la opción elegida para detectar acciones especiales (como cruzar el río)
            try:
                idx_op = int(eleccion) - 1
                claves_op = list(escena.opciones.keys())
                opcion_elegida_texto = claves_op[idx_op] if 0 <= idx_op < len(claves_op) else ""
            except Exception:
                opcion_elegida_texto = ""

            # Sonidos específicos de decisiones narrativas
            try:
                base_dir = os.path.dirname(__file__)
                # Meditar un momento -> MEDITATION-1.wav
                if "meditar un momento" in opcion_elegida_texto.lower():
                    med_path = os.path.join(base_dir, "Sound Effects", "MEDITATION-1.wav")
                    if os.path.exists(med_path):
                        play_effect(med_path)
                        self._last_meditation_time = time.time()
                # Escuchar los ecos -> ECHO-1.wav
                elif "escuchar los ecos" in opcion_elegida_texto.lower():
                    echo_path = os.path.join(base_dir, "Sound Effects", "ECHO-1.wav")
                    if os.path.exists(echo_path):
                        play_effect(echo_path)
                        self._last_echo_time = time.time()
                # Seguir adelante / Seguir (si no es combate directo) -> SOLIDWALK-1.wav (pasos sólidos especiales)
                elif opcion_elegida_texto.lower().startswith("seguir adelante") or opcion_elegida_texto.lower()=="seguir":
                    solid_path = os.path.join(base_dir, "Sound Effects", "SOLIDWALK-1.wav")
                    if os.path.exists(solid_path):
                        play_effect(solid_path)
                        self._last_solidwalk_time = time.time()
            except Exception:
                pass

            # Reproducir sonido de cofre al abrirlo (CHEST-1.wav) y luego buen/mal resultado en escenas resultantes
            chest_open_played = False
            chest_result_played = False
            try:
                base_dir = os.path.dirname(__file__)
                chest_scenes = {"cofre", "cofre_bosque", "cofre_bruma_evento", "cofre_corrupto_evento"}
                if self.escena_actual in chest_scenes and "abrir" in opcion_elegida_texto.lower():
                    chest_path = os.path.join(base_dir, "Sound Effects", "CHEST-1.wav")
                    if os.path.exists(chest_path):
                        play_effect(chest_path)
                        chest_open_played = True
                        self._last_chestopen_time = time.time()
                # Sonidos para resultados buenos/malos (cuando se entra a escenas *_bueno / *_malo)
                if isinstance(siguiente, str) and (siguiente.endswith("_bueno") or siguiente.endswith("_malo")):
                    good = siguiente.endswith("_bueno")
                    # candidatos por orden de preferencia (los primeros quizá no existen aún)
                    if good:
                        candidates = ["POSITIVE-1.wav", "WINBATTLE-1.wav", "SELECT2-1.wav", "SELECT1-1.wav"]
                    else:
                        candidates = ["BAD-1.wav", "LOSE-1.wav", "SELECT2-1.wav", "SELECT1-1.wav"]
                    chosen = None
                    for fname in candidates:
                        p = os.path.join(base_dir, "Sound Effects", fname)
                        if os.path.exists(p):
                            chosen = p
                            break
                    if chosen:
                        if chest_open_played:
                            time.sleep(0.25)
                        play_effect(chosen)
                        chest_result_played = True
                        # dar un respiro mínimo antes de más efectos que puedan cortar
                        time.sleep(0.15)
                        if good:
                            self._last_positive_time = time.time()
                        else:
                            self._last_bad_time = time.time()
            except Exception:
                pass

            # Sonido mítico / guardián (ANGEL-1.wav) al interactuar con lugares sagrados
            try:
                angel_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "ANGEL-1.wav")
                will_play = False
                # Colocar la piedra en la montaña
                if self.escena_actual == "montaña" and "colocar" in opcion_elegida_texto.lower():
                    will_play = True
                # Hablar / decidir frente a la guardiana (al escoger en la cueva). Solo una vez.
                if self.escena_actual == "cueva" and opcion_elegida_texto and not hasattr(self, "_guardian_angel_played"):
                    will_play = True
                    self._guardian_angel_played = True
                if will_play and os.path.exists(angel_path):
                    play_effect(angel_path)
                    self._last_angel_time = time.time()
                    # Delay para que no sea cortado por impresión / siguiente transición
                    time.sleep(5)
            except Exception:
                pass

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

            # Si estamos saliendo de la cueva, detener ambiente de cueva
            try:
                if self.escena_actual == "cueva" and siguiente != "cueva":
                    try:
                        if self.cave_src is not None:
                            self.cave_src.stop()
                    except Exception:
                        pass
                    self.cave_src = None
                    if self.cave_winsound and sys.platform.startswith("win"):
                        try:
                            import winsound
                            winsound.PlaySound(None, 0)
                        except Exception:
                            pass
                    self.cave_winsound = False
            except Exception:
                pass

            # Reproducir sonido de selección (omitido si un resultado de cofre acaba de sonar)
            # Si se acaba de meditar, evitar reproducir sonido de selección para no cortar la meditación
            recently_meditated = hasattr(self, "_last_meditation_time") and (time.time() - getattr(self, "_last_meditation_time")) < 2.5
            recently_echo = hasattr(self, "_last_echo_time") and (time.time() - getattr(self, "_last_echo_time")) < 2.0
            if not chest_result_played and not recently_meditated and not recently_echo:
                try:
                    sfx_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "SELECT3-1.wav")
                    if os.path.exists(sfx_path):
                        played = False
                        try:
                            from openal import oalOpen
                            sel_src = oalOpen(sfx_path)
                            if sel_src is not None:
                                try:
                                    sel_src.set_gain(0.8)
                                except Exception:
                                    try:
                                        sel_src.gain = 0.8
                                    except Exception:
                                        pass
                                sel_src.play()
                                played = True
                        except Exception:
                            pass
                        if not played:
                            play_effect(sfx_path)
                except Exception:
                    pass

            # Reproducir sonido de pasos (omitido si resultado cofre acaba de sonar)
            try:
                if not siguiente.startswith("final"):
                    # No reproducir pasos si CROSSRIVER acaba de sonar (ventana 0.5s)
                    recent_cross = hasattr(self, "_last_crossriver_time") and (time.time() - getattr(self, "_last_crossriver_time")) < 0.5
                    # No reproducir pasos si ANGEL acaba de sonar (ventana 0.5s)
                    recent_angel = hasattr(self, "_last_angel_time") and (time.time() - getattr(self, "_last_angel_time")) < 0.5
                    recent_echo = hasattr(self, "_last_echo_time") and (time.time() - getattr(self, "_last_echo_time")) < 2.0
                    # No reproducir pasos inmediatamente después de meditar para no cortar el sonido
                    recent_meditation = hasattr(self, "_last_meditation_time") and (time.time() - getattr(self, "_last_meditation_time")) < 2.5
                    cruzando = (self.escena_actual == "rio" and "cruzar" in opcion_elegida_texto.lower())
                    if (not cruzando and not recent_cross and not chest_open_played and not recent_angel and 
                        not chest_result_played and not recent_meditation and not recent_echo):
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

            # Si el siguiente estado es 'cueva', reproducir ambiente de cueva similar al río
            try:
                if siguiente == "cueva":
                    cave_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "CAVE-1.wav")
                    if os.path.exists(cave_path):
                        # Preferir openal para no interferir con pasos (que usan play_effect)
                        try:
                            from openal import oalOpen
                            c_src = oalOpen(cave_path)
                            if c_src is not None:
                                # bajar volumen al 25% para que no opaque otros efectos
                                try:
                                    c_src.set_gain(0.25)
                                except Exception:
                                    try:
                                        c_src.gain = 0.25
                                    except Exception:
                                        pass
                                # intentar loop si la implementación lo permite
                                try:
                                    c_src.set_looping(True)
                                except Exception:
                                    try:
                                        c_src.looping = True
                                    except Exception:
                                        pass
                                c_src.play()
                                self.cave_src = c_src
                                self.cave_winsound = False
                        except Exception:
                            # fallback winsound solo si no se está usando winsound para música principal para minimizar cortes
                            if sys.platform.startswith("win") and not self.winsound_used:
                                try:
                                    import winsound
                                    winsound.PlaySound(cave_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                                    self.cave_src = None
                                    self.cave_winsound = True
                                except Exception:
                                    pass
            except Exception:
                pass

            # Si la escena es un final, terminar
            if siguiente.startswith("final"):
                self.console.print("\n[bold red]--- FIN DEL JUEGO ---[/]\n")
                self.escenas[siguiente].mostrar(self.console)
                if siguiente == "final_oscuro":
                    try:
                        input("Presiona Enter para finalizar...")
                    except (KeyboardInterrupt, EOFError):
                        pass
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

                    # cueva (openal)
                    try:
                        if self.cave_src is not None:
                            self.cave_src.stop()
                    except Exception:
                        pass
                    self.cave_src = None
                    # cueva (winsound)
                    if self.cave_winsound and sys.platform.startswith("win"):
                        try:
                            import winsound
                            winsound.PlaySound(None, 0)
                        except Exception:
                            pass
                    self.cave_winsound = False

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
def descanso_breve_accion(j):
    """Acción de descanso breve con límite de 3 usos.

    Cura +8 salud hasta 3 veces. A partir de la 4ª vez solo muestra mensaje sin curar.
    """
    from rich.console import Console
    c = Console()
    if getattr(j, 'descansos', 0) >= 3:
        c.print("[yellow]Ya has usado todos tus descansos (3). No recuperas más salud.[/]")
        return "sendero_profundo"
    if j.salud >= j.salud_max:
        c.print("[dim]Tu salud ya está completa. No consumes un descanso.[/]")
        return "sendero_profundo"
    j.descansos += 1
    antes = j.salud
    j.salud = min(j.salud_max, j.salud + 10)
    c.print(f"[green]Descansas ({j.descansos}/3). Salud {antes} -> {j.salud} (+{j.salud-antes})[/]")
    return "sendero_profundo"

def sendero_profundo_accion(j):
    """Acción previa de la escena 'sendero_profundo' que oculta la opción de descanso tras 3 usos."""
    try:
        if getattr(j, 'descansos', 0) >= 3 and JUEGO_REF is not None:
                sc = JUEGO_REF.escenas.get("sendero_profundo")
                if sc and "Tomar un breve descanso" in sc.opciones:
                    # Crear nuevo dict sin la opción de descanso
                    nuevas = {k:v for k,v in sc.opciones.items() if k != "Tomar un breve descanso"}
                    sc.opciones = nuevas
    except Exception:
        pass
    return None

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
            {"Avanzar": "pelea",
             "Tomar el sendero sombrío": "sendero_sombrio",
             "Explorar el claro antiguo": "claro_antiguo"}
        ),
        "pelea": Escena(
            "¡Combate!",
            "Una bestia sombría bloquea tu camino. Debes luchar para avanzar.",
            {"Luchar": "combate"},
            accion=None
        ),
        # Ruta alternativa - enemigo 1
        "sendero_sombrio": Escena(
            "Sendero sombrío",
            "La luz casi no atraviesa las copas. Un gruñido se escucha entre los arbustos.",
            {"Avanzar sigilosamente": "combate_lobo", "Retroceder": "encrucijada"}
        ),
        "combate_lobo": Escena(
            "Combate: Lobo",
            "Un Lobo Sombrío salta hacia ti.",
            {},
            accion=combate_personalizado(1, "respiro_bruma")
        ),
        # Claro antiguo con trampa y ruta a laberinto
        "claro_antiguo": Escena(
            "Claro antiguo",
            "Piedras cubiertas de musgo forman un círculo. Algo de magia antigua persiste.",
            {"Investigar las ruinas": "trampa_enredaderas", "Seguir entre las piedras": "ruinas", "Regresar": "encrucijada"}
        ),
        "trampa_enredaderas": Escena(
            "Trampa de enredaderas",
            "Enredaderas vivas aprietan tus piernas infligiendo dolor.",
            {},
            accion=lambda j: (setattr(j,'salud', max(1,j.salud- (8 + getattr(j,'nivel_progreso',0)*3))) or "ruinas")
        ),
        "ruinas": Escena(
            "Ruinas antiguas",
            "Un arco derruido revela un corredor serpenteante: tal vez un laberinto.",
            {"Entrar al laberinto": "laberinto", "Regresar": "encrucijada"}
        ),
        "laberinto": Escena(
            "Laberinto místico",
            "Un susurro te guía y te confunde a la vez.",
            {},
            accion=laberinto_action
        ),
        # Combates avanzados disponibles tras progreso
        "combate_espectro": Escena(
            "Combate: Espectro",
            "La temperatura baja; un espectro emerge.",
            {},
            accion=combate_personalizado(2, "respiro_corrupto")
        ),
        "combate_guardiana": Escena(
            "Combate: Guardiana Corrompida",
            "La guardiana final intenta impedir tu avance.",
            {},
            accion=combate_personalizado(3, "claro_final")
        ),
        "combate": Escena(
            "Combate contra la bestia",
            "¡Prepárate para pelear!",
            {},
            accion=combate
        ),
        # Nueva progresión orgánica tras cada victoria
        "sendero_profundo": Escena(
            "Sendero profundo",
            "Tras la victoria, avanzas por un sendero que se estrecha. El bosque parece observarte.",
            {"Seguir huellas profundas": "combate_lobo", "Seguir susurros lejanos": "claro_susurros", "Visitar la tienda": "tienda_bosque"},
            accion=sendero_profundo_accion
        ),
        # ---------------- Post-combate secuencias nuevas ---------------- #
        # Tras primer combate (bestia)
        "respiro_bosque": Escena(
            "Respiro del bosque",
            "El aire se siente más ligero tras la batalla. Hojas caen lentamente mientras evalúas tus heridas.",
            {"Seguir adelante": "cofre_bosque", "Escuchar los ecos": "eco_lejano"}
        ),
        "cofre_bosque": Escena(
            "Cofre entre raíces",
            "Entre raíces retorcidas aparece un pequeño cofre cubierto de musgo.",
            {"Abrir el cofre": "cofre_bosque_abierto", "Ignorarlo y avanzar": "eco_lejano"}
        ),
        "cofre_bosque_abierto": Escena(
            "Interior del cofre",
            "Dentro brilla una luz y una sombra palpita inestable.",
            {"Tomar la luz": "cofre_bosque_bueno", "Tocar la sombra": "cofre_bosque_malo"}
        ),
        "eco_lejano": Escena(
            "Ecos lejanos",
            "Un eco distante te guía hacia un sendero más profundo.",
            {"Avanzar": "sendero_profundo"}
        ),
        # Tras combate del lobo
        "respiro_bruma": Escena(
            "Respiro en la bruma",
            "La neblina se separa unos instantes permitiéndote recuperar el aliento.",
            {"Seguir": "cofre_bruma_evento", "Meditar un momento": "susurro_distante"}
        ),
        "cofre_bruma_evento": Escena(
            "Cofre envuelto en bruma",
            "La bruma gira alrededor de un cofre con inscripciones desvaídas.",
            {"Abrir el cofre": "cofre_bruma_abierto", "Ignorarlo y seguir": "susurro_distante"}
        ),
        "cofre_bruma_abierto": Escena(
            "Elección difusa",
            "Al abrirlo, ves un fulgor cálido y una esfera fría que absorbe luz.",
            {"Tomar el fulgor": "cofre_bruma_bueno", "Tomar la esfera": "cofre_bruma_malo"}
        ),
        "susurro_distante": Escena(
            "Susurro distante",
            "Un susurro persistente te empuja hacia zonas más densas de bruma.",
            {"Adentrarte": "bosque_bruma"}
        ),
        # Tras combate del espectro
        "respiro_corrupto": Escena(
            "Respiro de corrupción",
            "El aire viciado se aquieta, como si la derrota del espectro hubiera debilitado la podredumbre.",
            {"Seguir avanzando": "cofre_corrupto_evento", "Observar el terreno": "latido_sombra"}
        ),
        "cofre_corrupto_evento": Escena(
            "Cofre ennegrecido",
            "Un cofre agrietado rezuma hilos oscuros.",
            {"Abrir el cofre": "cofre_corrupto_abierto", "Ignorarlo y continuar": "latido_sombra"}
        ),
        "cofre_corrupto_abierto": Escena(
            "Decisión corrupta",
            "Dentro, una chispa pura lucha contra un fragmento oscuro.",
            {"Tomar la chispa": "cofre_corrupto_bueno", "Tomar el fragmento": "cofre_corrupto_malo"}
        ),
        "latido_sombra": Escena(
            "Latido de la sombra",
            "Sientes un latido subterráneo que marca el camino hacia el corazón corrupto.",
            {"Seguir el latido": "claro_corrupto"}
        ),
        "claro_susurros": Escena(
            "Claro de susurros",
            "Los susurros te rodean; una figura lupina emerge entre la niebla.",
            {},
            accion=lambda j: "combate_lobo"
        ),
        "descanso_breve": Escena(
            "Descanso breve",
            "Encuentras un tronco donde recuperas el aliento (+10 salud). (Máx 3 descansos)",
            {},
            accion=descanso_breve_accion
        ),
        "bosque_bruma": Escena(
            "Bosque de bruma",
            "Una bruma fría serpentea entre los árboles, distorsionando formas.",
            {"Avanzar hacia la bruma densa": "combate_espectro", "Rodear buscando claridad": "trampa_bruma", "Buscar una luz titilante": "luz_bruma", "Visitar la tienda": "tienda_bruma"}
        ),
        "trampa_bruma": Escena(
            "Trampa en la bruma",
            "Tropezas con raíces ocultas (-6 salud).",
            {},
            accion=lambda j: (setattr(j,'salud', max(1, j.salud-6)) or "combate_espectro")
        ),
        "luz_bruma": Escena(
            "Luz titilante",
            "Una luz cálida alivia tus heridas (+5 salud) antes de desvanecerse.",
            {},
            accion=lambda j: (setattr(j,'salud', min(j.salud_max, j.salud+5)) or "combate_espectro")
        ),
        "claro_corrupto": Escena(
            "Claro corrupto",
            "El suelo palpita con energía oscura alrededor de un corazón de corrupción.",
            {"Enfrentar el corazón": "combate_guardiana", "Intentar purificar el aire": "purificacion_fallida", "Retirarse momentáneamente": "reagrupacion", "Visitar la tienda": "tienda_corrupta"}
        ),
        "purificacion_fallida": Escena(
            "Purificación fallida",
            "La corrupción te hiere (-10 salud) mientras intentas dispersarla.",
            {},
            accion=lambda j: (setattr(j,'salud', max(1, j.salud-10)) or "combate_guardiana")
        ),
        "reagrupacion": Escena(
            "Reagrupación",
            "Respiras hondo y recuperas fuerzas (+6 salud).",
            {},
            accion=lambda j: (setattr(j,'salud', min(j.salud_max, j.salud+6)) or "claro_corrupto")
        ),
        "claro_final": Escena(
            "Eco de la guardiana",
            "Con la guardiana derrotada, sientes caminos que se abren hacia un destino mayor.",
            {},
            accion=lambda j: ("montaña" if getattr(j,'tiene_piedra', False) else "cueva")
        ),

        # Tiendas
        "tienda_bosque": Escena(
            "Tienda del Bosque",
            "Un viajero ofrece objetos útiles entre raíces retorcidas.",
            {},
            accion=tienda_factory("sendero_profundo")
        ),
        "tienda_bruma": Escena(
            "Tienda de la Bruma",
            "Una figura encapuchada vende reliquias envueltas en vapor frío.",
            {},
            accion=tienda_factory("bosque_bruma")
        ),
        "tienda_corrupta": Escena(
            "Tienda Corrupta",
            "Una mesa erosionada por la corrupción ofrece poder a cambio de monedas.",
            {},
            accion=tienda_factory("claro_corrupto")
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

    # Acciones dinámicas para cofres (buenas/malas) reutilizables
    def chest_good_action(next_scene):
        def _a(j):
            console = Console()
            base_dir = os.path.dirname(__file__)
            # 50% monedas / curación
            if random.choice([True, False]):
                if j.salud >= j.salud_max:
                    j.monedas += 1
                    console.print("[dim]Energía curativa desaprovechada. Obtienes 1 moneda.[/]")
                else:
                    heal = random.randint(10,15)
                    antes = j.salud
                    j.salud = min(j.salud_max, j.salud + heal)
                    console.print(f"[green]Energía benevolente: Salud {antes}->{j.salud} (+{j.salud-antes}).[/]")
            else:
                gain = random.randint(2,5)
                j.monedas += gain
                console.print(f"[yellow]Encuentras {gain} monedas brillantes. Total: {j.monedas}[/]")
            # reproducir sonido positivo con fallback
            positive_candidates = ["POSITIVE-1.wav", "WINBATTLE-1.wav", "SELECT2-1.wav", "SELECT1-1.wav"]
            for fname in positive_candidates:
                pos_path = os.path.join(base_dir, "Sound Effects", fname)
                if os.path.exists(pos_path):
                    play_effect(pos_path)
                    break
            return next_scene
        return _a

    def chest_bad_action(next_scene):
        def _a(j):
            console = Console()
            base_dir = os.path.dirname(__file__)
            if random.choice([True, False]):
                loss = random.randint(1,3)
                loss = min(loss, j.monedas)
                j.monedas -= loss
                console.print(f"[red]Un gas tóxico corroe tus provisiones. Pierdes {loss} monedas. Total: {j.monedas}[/]")
            else:
                dmg = random.randint(5,10)
                j.salud = max(1, j.salud - dmg)
                console.print(f"[red]Una descarga oscura te hiere (-{dmg}). Salud: {j.salud}[/]")
            # reproducir sonido negativo con fallback
            negative_candidates = ["BAD-1.wav", "LOSE-1.wav", "SELECT2-1.wav", "SELECT1-1.wav"]
            for fname in negative_candidates:
                bad_path = os.path.join(base_dir, "Sound Effects", fname)
                if os.path.exists(bad_path):
                    play_effect(bad_path)
                    break
            return next_scene
        return _a

    # Asignar acciones a escenas de cofres
    escenas["cofre_bosque_bueno"] = Escena("Cofre del bosque (bueno)", "La luz te envuelve.", {}, accion=chest_good_action("eco_lejano"))
    escenas["cofre_bosque_malo"] = Escena("Cofre del bosque (malo)", "La sombra se agita.", {}, accion=chest_bad_action("eco_lejano"))
    escenas["cofre_bruma_bueno"] = Escena("Cofre de la bruma (bueno)", "El fulgor te fortalece.", {}, accion=chest_good_action("susurro_distante"))
    escenas["cofre_bruma_malo"] = Escena("Cofre de la bruma (malo)", "La esfera drena energía.", {}, accion=chest_bad_action("susurro_distante"))
    escenas["cofre_corrupto_bueno"] = Escena("Cofre corrupto (bueno)", "La chispa rechaza la corrupción.", {}, accion=chest_good_action("latido_sombra"))
    escenas["cofre_corrupto_malo"] = Escena("Cofre corrupto (malo)", "El fragmento oscuro se quiebra liberando dolor.", {}, accion=chest_bad_action("latido_sombra"))

    return escenas

if __name__ == "__main__":
    main()