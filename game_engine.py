import os
import sys
import time
import random
from rich.console import Console

from utils import TERRAIN_FOREST, TERRAIN_SOLID, REST_SENTINEL, JUEGO_REF
from audio_manager import (
    play_fight_music, stop_fight_audio, play_bg_music, stop_bg_audio,
    create_ambient_source, stop_ambient_source, cleanup_all_audio, play_effect
)


class Juego:
    def __init__(self, jugador, escenas, inicio):
        self.jugador = jugador
        self.escenas = escenas
        self.escena_actual = inicio
        self.console = Console()
        self.bg_audio_source = None
        self.oal_quit = None
        self.winsound_used = False
        self.river_src = None
        self.river_winsound = False
        self.cave_src = None
        self.cave_winsound = False
        self.fight_src = None
        self.fight_winsound = False

    def run(self):
        import utils
        utils.JUEGO_REF = self
        
        self.console.print("[bold magenta]¡Bienvenido a Adventure Time versión texto![/]")

        while True:
            try:
                escena = self.escenas[self.escena_actual]
            except KeyError:
                self._create_fallback_scenes()
                escena = self.escenas.get(self.escena_actual)
                if escena is None:
                    self.console.print(f"[red]Escena perdida: {self.escena_actual}. Redirigiendo al sendero profundo.[/]")
                    self.escena_actual = 'sendero_profundo'
                    escena = self.escenas[self.escena_actual]

            self._inject_rest_option(escena)

            if self.escena_actual.startswith("final"):
                self._handle_final_scene(escena)
                break

            siguiente_accion = None
            if escena.accion:
                was_fight = self._is_combat_scene(self.escena_actual)
                if was_fight:
                    self._start_combat_music()
                resultado = escena.accion(self.jugador)

                if was_fight:
                    self._end_combat_music(resultado)

                if resultado:
                    siguiente_accion = resultado

            if siguiente_accion:
                if siguiente_accion == "reiniciar":
                    self._handle_restart()
                    continue
                self.escena_actual = siguiente_accion
                continue

            escena.mostrar(self.console)
            eleccion = input("\n¿Qué decides hacer?: ")
            destino_tmp = escena.elegir(eleccion)
            
            if destino_tmp == REST_SENTINEL:
                self._handle_rest_action()
                continue
                
            siguiente = destino_tmp

            if not siguiente:
                self.console.print("[red]Opción no válida[/]")
                continue

            siguiente = self._handle_combat_gating(siguiente)

            opcion_elegida_texto = self._get_selected_option_text(escena, eleccion)

            self._play_narrative_sounds(opcion_elegida_texto)

            chest_open_played, chest_result_played = self._handle_chest_sounds(opcion_elegida_texto, siguiente)

            self._handle_guardian_sounds(opcion_elegida_texto)

            self._handle_river_crossing(escena, eleccion)

            self._handle_river_exit(siguiente)

            self._handle_cave_exit(siguiente)

            self._play_selection_sound(chest_result_played, opcion_elegida_texto)

            self._play_footstep_sounds(siguiente, opcion_elegida_texto, chest_open_played, chest_result_played)

            self._handle_river_entry(siguiente)

            self._handle_cave_entry(siguiente)

            if siguiente.startswith("final"):
                self._handle_final_transition(siguiente)
                break

            self.escena_actual = siguiente

    def _create_fallback_scenes(self):
        from scenes import Escena
        
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
            
        fallback_scenes = {
            'cofre_bosque_bueno': ("Cofre bosque (bueno)", "Emergencia.", {}, _fallback_good("eco_lejano")),
            'cofre_bosque_malo': ("Cofre bosque (malo)", "Emergencia.", {}, _fallback_bad("eco_lejano")),
            'cofre_bruma_bueno': ("Cofre bruma (bueno)", "Emergencia.", {}, _fallback_good("susurro_distante")),
            'cofre_bruma_malo': ("Cofre bruma (malo)", "Emergencia.", {}, _fallback_bad("susurro_distante")),
            'cofre_corrupto_bueno': ("Cofre corrupto (bueno)", "Emergencia.", {}, _fallback_good("latido_sombra")),
            'cofre_corrupto_malo': ("Cofre corrupto (malo)", "Emergencia.", {}, _fallback_bad("latido_sombra"))
        }
        
        for scene_name, (titulo, desc, opciones, accion) in fallback_scenes.items():
            if scene_name not in self.escenas:
                self.escenas[scene_name] = Escena(titulo, desc, opciones, accion=accion)

    def _inject_rest_option(self, escena):
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

    def _handle_final_scene(self, escena):
        self.console.print("\n[bold red]--- FIN DEL JUEGO ---[/]\n")
        escena.mostrar(self.console)
        if self.escena_actual == "final_oscuro":
            try:
                input("Presiona Enter para finalizar...")
            except (KeyboardInterrupt, EOFError):
                pass
        cleanup_all_audio()

    def _is_combat_scene(self, scene_name):
        combate_scenes = {"combate","combate_lobo","combate_espectro","combate_guardiana"}
        return scene_name in combate_scenes

    def _start_combat_music(self):
        try:
            if self.bg_audio_source is not None:
                try:
                    self.bg_audio_source.stop()
                except Exception:
                    pass
            if self.winsound_used and sys.platform.startswith("win"):
                try:
                    import winsound
                    winsound.PlaySound(None, 0)
                except Exception:
                    pass
            stop_ambient_source(self.river_src, self.river_winsound)
            self.river_src = None
            self.river_winsound = False
            fight_result = play_fight_music()
            if isinstance(fight_result, bool) and fight_result:
                self.fight_src = None
                self.fight_winsound = True
            else:
                self.fight_src = fight_result
                self.fight_winsound = False
        except Exception:
            pass

    def _end_combat_music(self, resultado):
        try:
            if self.fight_src is not None:
                try:
                    self.fight_src.stop()
                except Exception:
                    pass
            self.fight_src = None
            
            if resultado != "final_oscuro":
                if self.fight_winsound and sys.platform.startswith("win"):
                    try:
                        import winsound
                        adv_path = os.path.join(os.path.dirname(__file__), "Music", "ADVENTURE-1.wav")
                        if os.path.exists(adv_path):
                            winsound.PlaySound(adv_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                            self.winsound_used = True
                        else:
                            winsound.PlaySound(None, 0)
                    except Exception:
                        pass
                if self.bg_audio_source is not None:
                    try:
                        self.bg_audio_source.play()
                    except Exception:
                        pass
                else:
                    self.bg_audio_source = play_bg_music()
            else:
                if self.fight_winsound and sys.platform.startswith("win"):
                    try:
                        import winsound
                        winsound.PlaySound(None, 0)
                    except Exception:
                        pass
            self.fight_winsound = False
        except Exception:
            pass

    def _handle_restart(self):
        if self.fight_src is not None:
            try:
                self.fight_src.stop()
            except Exception:
                pass
        self.fight_src = None
        self.fight_winsound = False
        
        self.bg_audio_source = play_bg_music()
        if self.bg_audio_source is None and sys.platform.startswith("win"):
            self.winsound_used = True
        
        self.escena_actual = "inicio"

    def _handle_rest_action(self):
        try:
            if getattr(self.jugador,'descansos',0) >= 3:
                self.console.print("[yellow]Ya no puedes descansar más (3/3).[/]")
            else:
                if self.jugador.salud >= self.jugador.salud_max:
                    self.console.print("[dim]Tu salud ya está completa. No consumes un descanso.[/]")
                else:
                    # Reproducir sonido de descanso
                    from audio_manager import play_effect
                    import os
                    rest_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "REST-1.wav")
                    if os.path.exists(rest_path):
                        play_effect(rest_path)
                    
                    antes = self.jugador.salud
                    self.jugador.salud = min(self.jugador.salud_max, self.jugador.salud + 10)
                    self.jugador.descansos += 1
                    self.console.print(f"[green]Descansas ({self.jugador.descansos}/3). Salud {antes} -> {self.jugador.salud} (+{self.jugador.salud-antes})[/]")
        except Exception:
            pass

    def _handle_combat_gating(self, siguiente):
        try:
            contador = getattr(self.jugador, 'decisiones_desde_ultimo_combate', 0)
            if str(siguiente).startswith("combate") and contador < 3:
                self.console.print("[yellow]Aún no estás listo para otro combate. Exploras un poco más...[/]")
                mapping = {
                    'combate': 'encrucijada',
                    'combate_lobo': 'eco_lejano',
                    'combate_espectro': 'bosque_bruma',
                    'combate_guardiana': 'claro_corrupto'
                }
                siguiente = mapping.get(siguiente, 'encrucijada')
                contador += 1
                setattr(self.jugador, 'decisiones_desde_ultimo_combate', contador)
            elif (not str(siguiente).startswith("combate")) and (not str(siguiente).startswith("final")):
                contador += 1
                setattr(self.jugador, 'decisiones_desde_ultimo_combate', contador)
        except Exception:
            pass
        return siguiente

    def _get_selected_option_text(self, escena, eleccion):
        try:
            idx_op = int(eleccion) - 1
            claves_op = list(escena.opciones.keys())
            return claves_op[idx_op] if 0 <= idx_op < len(claves_op) else ""
        except Exception:
            return ""

    def _play_narrative_sounds(self, opcion_elegida_texto):
        try:
            base_dir = os.path.dirname(__file__)
            if "meditar un momento" in opcion_elegida_texto.lower():
                med_path = os.path.join(base_dir, "Sound Effects", "MEDITATION-1.wav")
                if os.path.exists(med_path):
                    play_effect(med_path)
                    self._last_meditation_time = time.time()
            elif "escuchar los ecos" in opcion_elegida_texto.lower():
                echo_path = os.path.join(base_dir, "Sound Effects", "ECHO-1.wav")
                if os.path.exists(echo_path):
                    play_effect(echo_path)
                    self._last_echo_time = time.time()
            elif "entrar a la cabaña" in opcion_elegida_texto.lower():
                door_path = os.path.join(base_dir, "Sound Effects", "OPENDOOR-1.wav")
                solid_path = os.path.join(base_dir, "Sound Effects", "SOLIDWALK-1.wav")
                
                # Reproducir ambos sonidos al mismo tiempo usando threading
                import threading
                
                def play_door():
                    if os.path.exists(door_path):
                        play_effect(door_path)
                
                def play_steps():
                    time.sleep(0.05)  # Delay muy corto para solapamiento más pronunciado
                    if os.path.exists(solid_path):
                        play_effect(solid_path)
                
                # Iniciar ambos sonidos en threads separados
                thread_door = threading.Thread(target=play_door)
                thread_steps = threading.Thread(target=play_steps)
                
                thread_door.start()
                thread_steps.start()
                
                self._last_solidwalk_time = time.time()
            elif "buscar pistas en el interior" in opcion_elegida_texto.lower():
                solid_path = os.path.join(base_dir, "Sound Effects", "SOLIDWALK-1.wav")
                if os.path.exists(solid_path):
                    play_effect(solid_path)
                    self._last_solidwalk_time = time.time()
            elif opcion_elegida_texto.lower().startswith("seguir adelante") or opcion_elegida_texto.lower()=="seguir":
                solid_path = os.path.join(base_dir, "Sound Effects", "SOLIDWALK-1.wav")
                if os.path.exists(solid_path):
                    play_effect(solid_path)
                    self._last_solidwalk_time = time.time()
        except Exception:
            pass

    def _handle_chest_sounds(self, opcion_elegida_texto, siguiente):
        chest_open_played = False
        chest_result_played = False
        try:
            base_dir = os.path.dirname(__file__)
            if "abrir" in opcion_elegida_texto.lower() and "cofre" in opcion_elegida_texto.lower():
                chest_path = os.path.join(base_dir, "Sound Effects", "CHEST-1.wav")
                if os.path.exists(chest_path):
                    play_effect(chest_path)
                    chest_open_played = True
                    self._last_chestopen_time = time.time()
                    
            if isinstance(siguiente, str) and (siguiente.endswith("_bueno") or siguiente.endswith("_malo")):
                good = siguiente.endswith("_bueno")
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
                    time.sleep(0.15)
                    if good:
                        self._last_positive_time = time.time()
                    else:
                        self._last_bad_time = time.time()
        except Exception:
            pass
        return chest_open_played, chest_result_played

    def _handle_guardian_sounds(self, opcion_elegida_texto):
        try:
            angel_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "ANGEL-1.wav")
            will_play = False
            if self.escena_actual == "montaña" and "colocar" in opcion_elegida_texto.lower():
                will_play = True
            if self.escena_actual == "cueva" and opcion_elegida_texto and not hasattr(self, "_guardian_angel_played"):
                will_play = True
                self._guardian_angel_played = True
            if will_play and os.path.exists(angel_path):
                play_effect(angel_path)
                self._last_angel_time = time.time()
                time.sleep(5)
        except Exception:
            pass

    def _handle_river_crossing(self, escena, eleccion):
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
                        play_effect(cr_path)
                        self._last_crossriver_time = time.time()
        except Exception:
            pass

    def _handle_river_exit(self, siguiente):
        try:
            if self.escena_actual == "rio" and siguiente != "rio":
                stop_ambient_source(self.river_src, self.river_winsound)
                self.river_src = None
                self.river_winsound = False
        except Exception:
            pass

    def _handle_cave_exit(self, siguiente):
        try:
            if self.escena_actual == "cueva" and siguiente != "cueva":
                stop_ambient_source(self.cave_src, self.cave_winsound)
                self.cave_src = None
                self.cave_winsound = False
        except Exception:
            pass

    def _play_selection_sound(self, chest_result_played, opcion_elegida_texto):
        recently_meditated = hasattr(self, "_last_meditation_time") and (time.time() - getattr(self, "_last_meditation_time")) < 2.5
        recently_echo = hasattr(self, "_last_echo_time") and (time.time() - getattr(self, "_last_echo_time")) < 2.0
        recently_crossriver = hasattr(self, "_last_crossriver_time") and (time.time() - getattr(self, "_last_crossriver_time")) < 0.6
        is_crossing = (self.escena_actual == "rio" and isinstance(opcion_elegida_texto, str) and "cruzar" in opcion_elegida_texto.lower())

    def _play_footstep_sounds(self, siguiente, opcion_elegida_texto, chest_open_played, chest_result_played):
        try:
            if not siguiente.startswith("final"):
                recent_cross = hasattr(self, "_last_crossriver_time") and (time.time() - getattr(self, "_last_crossriver_time")) < 0.5
                recent_angel = hasattr(self, "_last_angel_time") and (time.time() - getattr(self, "_last_angel_time")) < 0.5
                recent_echo = hasattr(self, "_last_echo_time") and (time.time() - getattr(self, "_last_echo_time")) < 2.0
                recent_meditation = hasattr(self, "_last_meditation_time") and (time.time() - getattr(self, "_last_meditation_time")) < 2.5
                cruzando = (self.escena_actual == "rio" and "cruzar" in opcion_elegida_texto.lower())
                
                if (not cruzando and not recent_cross and not chest_open_played and not recent_angel and 
                    not chest_result_played and not recent_meditation and not recent_echo):
                    base_dir = os.path.dirname(__file__)
                    # Usar SOLIDWALK si se está buscando pistas en el interior (dentro de la cabaña)
                    if "buscar pistas en el interior" in opcion_elegida_texto.lower():
                        step_path = os.path.join(base_dir, "Sound Effects", "SOLIDWALK-1.wav")
                    else:
                        step_path = os.path.join(base_dir, "Sound Effects", "FORESTWALK-1.wav") if siguiente in TERRAIN_FOREST else os.path.join(base_dir, "Sound Effects", "SOLIDWALK-1.wav")
                    if os.path.exists(step_path):
                        play_effect(step_path)
        except Exception:
            pass

    def _handle_river_entry(self, siguiente):
        try:
            if siguiente == "rio":
                river_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "RIVER-1.wav")
                self.river_src, self.river_winsound = create_ambient_source(river_path, volume=0.2)
        except Exception:
            pass

    def _handle_cave_entry(self, siguiente):
        try:
            if siguiente == "cueva":
                cave_path = os.path.join(os.path.dirname(__file__), "Sound Effects", "CAVE-1.wav")
                self.cave_src, self.cave_winsound = create_ambient_source(cave_path, volume=0.25, looping=True)
        except Exception:
            pass

    def _handle_final_transition(self, siguiente):
        self.console.print("\n[bold red]--- FIN DEL JUEGO ---[/]\n")
        self.escenas[siguiente].mostrar(self.console)
        if siguiente == "final_oscuro":
            try:
                input("Presiona Enter para finalizar...")
            except (KeyboardInterrupt, EOFError):
                pass
        cleanup_all_audio()