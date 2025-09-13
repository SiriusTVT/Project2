import os
import sys
import random
import time
from rich.console import Console
from utils import typewriter, REST_SENTINEL, laberinto_action, descanso_breve_accion, sendero_profundo_accion
from combat import combate, combate_personalizado
from audio_manager import play_store_music, stop_store_music, play_bg_music, stop_bg_audio, play_effect


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


def tienda_factory(retorno: str):
    def _tienda(j):
        console = Console()
        console.print("\n[bold cyan]Tienda del viajero[/]")
        
        stop_bg_audio()
        
        from audio_manager import LAST_SFX
        try:
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
        
        store_src, used_winsound_store = play_store_music()
        
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
            
            try:
                sel_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "SELECT3-1.wav")
                if os.path.exists(sel_path):
                    play_effect(sel_path)
            except Exception:
                pass
                
            if elec == '1':
                if j.monedas >= 5:
                    j.monedas -= 5
                    j.salud = min(j.salud_max, j.salud+20)
                    play_effect(os.path.join(os.path.dirname(__file__), "Sound Effects", "HEAL-1.wav"))
                    console.print(f"[green]Te curas. Salud: {j.salud}/{j.salud_max} (Monedas: {j.monedas})[/]")
                else:
                    console.print("[red]Monedas insuficientes.[/]")
            elif elec == '2':
                if j.monedas >= 9:
                    j.monedas -= 9
                    j.salud = j.salud_max
                    play_effect(os.path.join(os.path.dirname(__file__), "Sound Effects", "HEAL-1.wav"))
                    console.print(f"[green]Salud restaurada completamente. (Monedas: {j.monedas})[/]")
                else:
                    console.print("[red]Monedas insuficientes.[/]")
            elif elec == '3':
                if j.monedas >= 8:
                    j.monedas -= 8
                    j.danio += 3
                    play_effect(os.path.join(os.path.dirname(__file__), "Sound Effects", "SHARP-1.wav"))
                    console.print(f"[yellow]Tu daño aumenta a {j.danio}. (Monedas: {j.monedas})[/]")
                else:
                    console.print("[red]Monedas insuficientes.[/]")
            elif elec == '4':
                if j.amuleto_vigor:
                    console.print("[dim]Ya posees el amuleto.[/]")
                elif j.monedas >= 10:
                    j.monedas -= 10
                    j.salud_max += 10
                    j.salud = min(j.salud_max, j.salud+10)
                    j.amuleto_vigor = True
                    console.print(f"[green]Amuleto adquirido. Salud máx: {j.salud_max}. (Monedas: {j.monedas})[/]")
                else:
                    console.print("[red]Monedas insuficientes.[/]")
            elif elec == '5':
                if j.monedas >= 4:
                    j.monedas -= 4
                    j.poder_usos = 2
                    console.print(f"[magenta]Poderes restaurados (2 usos). (Monedas: {j.monedas})[/]")
                else:
                    console.print("[red]Monedas insuficientes.[/]")
            elif elec == '6' or elec == '':
                console.print("[dim]Abandonas la tienda.[/]")
                stop_store_music(store_src, used_winsound_store)
                # reanudar aventura (sin música)
                return retorno
            else:
                console.print("[red]Opción no válida.[/]")
    return _tienda


def crear_escenas():
    from utils import get_intro_lines
    intro_text = "\n".join(get_intro_lines())
    
    escenas = {
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
            accion=lambda jugador: (setattr(jugador, "tiene_piedra", True), None)[-1]
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
        "sendero_profundo": Escena(
            "Sendero profundo",
            "Tras la victoria, avanzas por un sendero que se estrecha. El bosque parece observarte.",
            {"Seguir huellas profundas": "combate_lobo", "Seguir susurros lejanos": "claro_susurros", "Visitar la tienda": "tienda_bosque"},
            accion=sendero_profundo_accion
        ),

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

    def chest_good_action(next_scene):
        def _a(j):
            console = Console()
            base_dir = os.path.dirname(__file__)
            chest_path = os.path.join(base_dir, "Sound Effects", "CHEST-1.wav")
            if os.path.exists(chest_path):
                play_effect(chest_path)
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
            chest_path = os.path.join(base_dir, "Sound Effects", "CHEST-1.wav")
            if os.path.exists(chest_path):
                play_effect(chest_path)
            if random.choice([True, False]):
                loss = random.randint(1,3)
                loss = min(loss, j.monedas)
                j.monedas -= loss
                console.print(f"[red]Un gas tóxico corroe tus provisiones. Pierdes {loss} monedas. Total: {j.monedas}[/]")
            else:
                dmg = random.randint(5,10)
                j.salud = max(1, j.salud - dmg)
                console.print(f"[red]Una descarga oscura te hiere (-{dmg}). Salud: {j.salud}[/]")
            negative_candidates = ["BAD-1.wav", "LOSE-1.wav", "SELECT2-1.wav", "SELECT1-1.wav"]
            for fname in negative_candidates:
                bad_path = os.path.join(base_dir, "Sound Effects", fname)
                if os.path.exists(bad_path):
                    play_effect(bad_path)
                    break
            return next_scene
        return _a
    escenas["cofre_bosque_bueno"] = Escena("Cofre del bosque (bueno)", "La luz te envuelve.", {}, accion=chest_good_action("eco_lejano"))
    escenas["cofre_bosque_malo"] = Escena("Cofre del bosque (malo)", "La sombra se agita.", {}, accion=chest_bad_action("eco_lejano"))
    escenas["cofre_bruma_bueno"] = Escena("Cofre de la bruma (bueno)", "El fulgor te fortalece.", {}, accion=chest_good_action("susurro_distante"))
    escenas["cofre_bruma_malo"] = Escena("Cofre de la bruma (malo)", "La esfera drena energía.", {}, accion=chest_bad_action("susurro_distante"))
    escenas["cofre_corrupto_bueno"] = Escena("Cofre corrupto (bueno)", "La chispa rechaza la corrupción.", {}, accion=chest_good_action("latido_sombra"))
    escenas["cofre_corrupto_malo"] = Escena("Cofre corrupto (malo)", "El fragmento oscuro se quiebra liberando dolor.", {}, accion=chest_bad_action("latido_sombra"))

    return escenas