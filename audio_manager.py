"""
Audio Manager Module for Adventure Time Game

Handles all audio functionality including OpenAL and winsound management,
audio references, and sound effects.
"""

import os
import sys
import time

# Referencias globales para audio
FIGHT_AUDIO_REF = {"src": None, "winsound": False}
BG_AUDIO_REF = {"src": None, "winsound": False}
DEFEAT_AUDIO = {"sources": [], "winsound": False}
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


def stop_fight_audio():
    """Detiene la música de combate."""
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


def stop_bg_audio():
    """Detiene la música de fondo."""
    try:
        global BG_AUDIO_REF
        if BG_AUDIO_REF.get("src") is not None:
            try:
                BG_AUDIO_REF["src"].stop()
            except Exception:
                pass
        if BG_AUDIO_REF.get("winsound") and sys.platform.startswith("win"):
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except Exception:
                pass
        BG_AUDIO_REF["src"] = None
        BG_AUDIO_REF["winsound"] = False
    except Exception:
        pass


def play_defeat_audio():
    """Reproduce audios de derrota (FAILBATTLE + LOSE) simultáneamente si es posible."""
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
    
    return played_openal


def stop_defeat_audio():
    """Detiene los audios de derrota."""
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


def play_fight_music(volume=0.3):
    """Reproduce música de combate."""
    fight_path = os.path.join(os.path.dirname(__file__), "Music", "FIGHT-1.wav")
    if os.path.exists(fight_path):
        played = False
        # Intentar siempre OpenAL primero
        try:
            from openal import oalOpen
            f_src = oalOpen(fight_path)
            if f_src is not None:
                try:
                    f_src.set_gain(volume)
                except Exception:
                    try: 
                        f_src.gain = volume
                    except Exception: 
                        pass
                f_src.play()
                try:
                    FIGHT_AUDIO_REF["src"] = f_src
                    FIGHT_AUDIO_REF["winsound"] = False
                except Exception:
                    pass
                played = True
                return f_src
        except Exception:
            pass
        # Si OpenAL no funcionó usar winsound si está en Windows
        if not played and sys.platform.startswith("win"):
            try:
                import winsound
                winsound.PlaySound(fight_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                try:
                    FIGHT_AUDIO_REF["src"] = None
                    FIGHT_AUDIO_REF["winsound"] = True
                except Exception:
                    pass
                played = True
                return True
            except Exception:
                pass
    return None


def play_bg_music(volume=0.2):
    """Reproduce música de aventura de fondo."""
    adventure_path = os.path.join(os.path.dirname(__file__), "Music", "ADVENTURE-1.wav")
    if os.path.exists(adventure_path):
        # intentar openal
        try:
            from openal import oalOpen
            adv_src = oalOpen(adventure_path)
            if adv_src is not None:
                try:
                    adv_src.set_gain(volume)
                except Exception:
                    try: 
                        adv_src.gain = volume
                    except Exception: 
                        pass
                adv_src.play()
                try:
                    BG_AUDIO_REF["src"] = adv_src
                    BG_AUDIO_REF["winsound"] = False
                except Exception:
                    pass
                return adv_src
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
                    return True
                except Exception:
                    pass
    return None


def play_intro_music(volume=0.2):
    """Reproduce música de introducción."""
    audio_path = os.path.join(os.path.dirname(__file__), "Music", "INTRO-1.wav")
    if os.path.exists(audio_path):
        try:
            from openal import oalOpen
            audio_source = oalOpen(audio_path)
            if audio_source is not None:
                try:
                    audio_source.set_gain(volume)
                except Exception:
                    try:
                        audio_source.gain = volume
                    except Exception:
                        pass
                audio_source.play()
                return audio_source
        except Exception:
            # fallback winsound en Windows
            try:
                if sys.platform.startswith("win"):
                    import winsound
                    winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    return True
            except Exception:
                pass
    return None


def play_narration():
    """Reproduce narración (NARRADOR.wav)."""
    narr_path = os.path.join(os.path.dirname(__file__), "Music", "NARRADOR.wav")
    if os.path.exists(narr_path):
        # intentar openal primero para no cortar la música intro
        try:
            from openal import oalOpen
            narr_source = oalOpen(narr_path)
            if narr_source is not None:
                narr_source.play()
                return narr_source, False
        except Exception:
            # fallback winsound (esto reemplazará la música intro si se usa winsound)
            if sys.platform.startswith("win"):
                try:
                    import winsound
                    winsound.PlaySound(narr_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                    return None, True
                except Exception:
                    pass
    return None, False


def stop_narration(narr_source, narr_winsound):
    """Detiene la narración."""
    try:
        if narr_source:
            narr_source.stop()
        if narr_winsound and sys.platform.startswith("win"):
            import winsound
            winsound.PlaySound(None, 0)
    except Exception:
        pass


def play_store_music(volume=0.25):
    """Reproduce música de tienda."""
    store_path = os.path.join(os.path.dirname(__file__), "Music", "STORE-1.wav")
    if os.path.exists(store_path):
        try:
            from openal import oalOpen
            store_src = oalOpen(store_path)
            if store_src is not None:
                try:
                    store_src.set_gain(volume)
                except Exception:
                    try: 
                        store_src.gain = volume
                    except Exception: 
                        pass
                store_src.play()
                return store_src, False
        except Exception:
            pass
        
        if sys.platform.startswith("win"):
            try:
                import winsound
                winsound.PlaySound(store_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return None, True
            except Exception:
                pass
    return None, False


def stop_store_music(store_src, used_winsound_store):
    """Detiene música de tienda."""
    try:
        if store_src is not None:
            try: 
                store_src.stop()
            except Exception: 
                pass
        if used_winsound_store and sys.platform.startswith("win"):
            try:
                import winsound
                winsound.PlaySound(None, 0)
            except Exception:
                pass
    except Exception:
        pass


def create_ambient_source(filepath, volume=0.2, looping=True):
    """Crea una fuente de audio ambiente (río, cueva, etc.)."""
    if os.path.exists(filepath):
        # Preferir openal
        try:
            from openal import oalOpen
            src = oalOpen(filepath)
            if src is not None:
                try:
                    src.set_gain(volume)
                except Exception:
                    try: 
                        src.gain = volume
                    except Exception: 
                        pass
                # intentar loop si la implementación lo permite
                if looping:
                    try:
                        src.set_looping(True)
                    except Exception:
                        try:
                            src.looping = True
                        except Exception:
                            pass
                src.play()
                return src, False
        except Exception:
            pass
        
        # fallback winsound
        if sys.platform.startswith("win"):
            try:
                import winsound
                winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return None, True
            except Exception:
                pass
    return None, False


def stop_ambient_source(src, winsound_flag):
    """Detiene una fuente de audio ambiente."""
    try:
        if src is not None:
            src.stop()
    except Exception:
        pass
    
    if winsound_flag and sys.platform.startswith("win"):
        try:
            import winsound
            winsound.PlaySound(None, 0)
        except Exception:
            pass


def cleanup_all_audio():
    """Limpia todas las fuentes de audio activas."""
    stop_fight_audio()
    stop_bg_audio()
    stop_defeat_audio()
    
    # Detener último efecto SFX
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