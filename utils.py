import time
import random
from rich.console import Console

TEXT_SPEED = 0.03

JUEGO_REF = None
REST_SENTINEL = "__DESCANSO_DYNAMIC__"

TERRAIN_FOREST = {"inicio", "izquierda", "rio", "rugido", "encrucijada"}
TERRAIN_SOLID = {"cabaña", "cofre", "mapa", "pelea", "combate", "montaña", "cueva", "final_heroico", "final_oscuro", "final_neutral", "sendero_profundo", "bosque_bruma", "claro_corrupto", "claro_final"}


def seleccionar_velocidad(console):
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


def typewriter(text, delay=None, console=None, style=None):
    if console is None:
        console = Console()
    if delay is None:
        delay = TEXT_SPEED
    for ch in text:
        console.print(ch, end="", style=style)
        time.sleep(delay)
    console.print("")


def get_intro_lines():
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


def generar_laberinto(tam):
    import random
    ancho = alto = tam
    lab = [[0]*ancho for _ in range(alto)]
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
        return "montaña" if jugador.tiene_piedra else "cueva"
    console.print("[bold red]Fracaso en el laberinto...[/]")
    return "final_oscuro"


def descanso_breve_accion(j):
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
    try:
        if getattr(j, 'descansos', 0) >= 3 and JUEGO_REF is not None:
                sc = JUEGO_REF.escenas.get("sendero_profundo")
                if sc and "Tomar un breve descanso" in sc.opciones:
                    nuevas = {k:v for k,v in sc.opciones.items() if k != "Tomar un breve descanso"}
                    sc.opciones = nuevas
    except Exception:
        pass
    return None