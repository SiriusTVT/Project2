import os
import random
import time
from rich.console import Console
from character import Enemigo, generar_enemigo
from audio_manager import play_effect, play_defeat_audio, stop_defeat_audio


def handle_derrota(jugador):
    console = Console()
    console.print("\n[bold red]Has sido derrotado...[/]")
    
    play_defeat_audio()
    while True:
        try:
            resp = input("¿Quieres intentarlo de nuevo desde el inicio? (s/n): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            resp = 'n'
        if resp.startswith('s'):
            stop_defeat_audio()
            if hasattr(jugador, 'restaurar'):
                jugador.restaurar()
            return "reiniciar"
        if resp.startswith('n') or resp == '':
            return "final_oscuro"
        console.print("[yellow]Opción no válida. Responde s o n.[/]")


def combate_personalizado(etapa: int, proxima_escena="sendero_profundo"):
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
                skip_enemy_attack = True 
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
                play_effect(os.path.join(os.path.dirname(__file__), "Sound Effects", "HEAL-1.wav"))
                time.sleep(0.5)  # Pausa para que se escuche el sonido
                dano_rebote = random.randint(1,10)
                jugador.salud = max(1, jugador.salud - dano_rebote)
                skip_enemy_attack = True
                console.print(f"[green]Te curas {curar}. [/][red]El enemigo aprovecha y te hiere (-{dano_rebote}). Salud actual: {jugador.salud}[/]")
            else:
                console.print("[red]Acción no válida[/]")
                continue
                
            if enemigo.salud > 0 and not skip_enemy_attack:
                base = enemigo.danio
                tipo = random.choice(["normal","fuerte"]) if etapa > 1 else "normal"
                if tipo == "fuerte":
                    base += 5
                if defensa:
                    base = 0
                    defensa = False
                    
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
                        
                if base > 0:
                    jugador.salud -= base
                    console.print(f"Recibes [red]{base}[/] de daño.")
                else:
                    console.print("[green]Bloqueas todo el ataque enemigo.[/]")
                    
            skip_enemy_attack = False
            time.sleep(0.4)
            
        if jugador.salud > 0:
            console.print(f"\n[bold green]¡Has derrotado a {enemigo.nombre}![/]")
            play_effect(os.path.join(os.path.dirname(__file__), "Sound Effects", "WINBATTLE-1.wav"))
            jugador.nivel_progreso = getattr(jugador,'nivel_progreso',0)+1
            recompensa = random.randint(5,15)
            jugador.monedas += recompensa
            console.print(f"[yellow]Obtienes {recompensa} monedas. Total: {jugador.monedas}[/]")
            jugador.combates_ganados += 1
            jugador.decisiones_desde_ultimo_combate = 0
            return proxima_escena
        else:
            return handle_derrota(jugador)
    return _accion


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
            play_effect(os.path.join(os.path.dirname(__file__), "Sound Effects", "HEAL-1.wav"))
            time.sleep(0.5)  # Pausa para que se escuche el sonido
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
                
            if danio_enemigo > 0:
                jugador.salud -= danio_enemigo
                console.print(f"{mensaje} Recibes [red]{danio_enemigo}[/] de daño.")
                
        skip_enemy_attack = False
        time.sleep(0.5)
        
    if jugador.salud > 0:
        console.print("\n[bold green]¡Has vencido a la bestia![/]")
        play_effect(os.path.join(os.path.dirname(__file__), "Sound Effects", "WINBATTLE-1.wav"))
        jugador.nivel_progreso = max(getattr(jugador, 'nivel_progreso', 0), 1)
        recompensa = random.randint(5,15)
        jugador.monedas += recompensa
        console.print(f"[yellow]Obtienes {recompensa} monedas. Total: {jugador.monedas}[/]")
        jugador.combates_ganados += 1
        jugador.decisiones_desde_ultimo_combate = 0
        return "respiro_bosque"
    else:
        return handle_derrota(jugador)