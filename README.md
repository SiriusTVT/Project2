# Adventure Time (Text-based Audio Game)

## Authors  
- **David Felipe Hurtado Marroquín** 
- **Juan David Troncoso Barona** 

## Project Description  
This project is a text-based adventure game inspired by *Zork*. The player explores a mysterious forest, makes choices, and faces enemies in turn-based battles. The game integrates a consistent auditory world using **OpenAL** and additional audio handling with *winsound* (for Windows compatibility).  

Key features include:  
- **Narrative gameplay**: a complete story with introduction, development, climax, and multiple endings.  
- **Audio spatialization**: environmental sounds (rivers, caves, forests) and effects (combat, footsteps, treasure chests) are positioned in 3D space according to the story.  
- **Interactive combat system**: turn-based battles with normal attacks, special powers, defense, and healing.  
- **Shops and economy**: players can buy items, heal, and upgrade stats using coins.  
- **Dynamic labyrinth**: randomly generated mazes with traps and progressive difficulty.  
- **Replayability**: multiple paths and endings depending on player choices.  

The game is fully playable in the console for at least 5 minutes, following the project requirements.

## Why We Designed It This Way  
- **Immersion through audio**: We prioritized spatialized audio to align with the story and actions, making sound an essential part of the experience.  
- **Object-Oriented Programming**: We structured the project with classes (`Personaje`, `Enemigo`, `Juego`, `Escena`) to keep the code modular, reusable, and maintainable.  
- **User engagement**: Turn-based combat and economy systems give players meaningful choices and rewards.  
- **Cross-platform audio**: We implemented *OpenAL* as the primary library for 3D sound, but added *winsound* fallback for compatibility on Windows machines.  
- **Scalability**: Scenes, items, and enemies can be easily extended or modified without breaking the main game loop.  

## Requirements  
- **Python 3.10+**  
- `rich` (for styled console output)  
- `openal` (for audio spatialization)  
- Audio files placed in the `Music` and `Sound Effects` folders as used by the code.  

Install dependencies with:  
```bash
pip install rich openal
