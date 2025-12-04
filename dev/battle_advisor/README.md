# AI Battle Advisor

Turn-by-turn skill recommender for Looney Tunes: World of Mayhem battles.

## Features

- **Interactive Battle Simulation**: Step through battles turn by turn
- **AI Skill Recommendations**: OpenAI-powered suggestions for best skill and target
- **Real-time Analysis**: Considers HP, buffs/debuffs, threat levels, and skill effects
- **Skill Metadata Integration**: Uses CSV data for accurate skill descriptions

## Quick Start

```bash
# Navigate to dev folder
cd /Users/himanshu.dahiya/Desktop/data/dev

# Activate virtual environment
source venv/bin/activate

# Run sample battle
python run_battle_advisor.py

# Or run with module syntax
python -m battle_advisor.main
```

## Usage

```bash
# List available battle logs
python run_battle_advisor.py --list

# Run a specific battle from logs
python run_battle_advisor.py --battle 1

# Run sample battle (default)
python run_battle_advisor.py --sample

# Run without AI (manual mode)
python run_battle_advisor.py --no-ai
```

## How It Works

### Each Turn:
1. **State Snapshot**: Captures current HP, buffs, debuffs, available skills
2. **AI Analysis**: Sends state to OpenAI for recommendation
3. **Recommendation Display**: Shows best skill + target with reasoning
4. **Player Choice**: Accept AI suggestion or choose your own action
5. **Apply Action**: Execute skill, update state, advance turn

### AI Considers:
- **Kill Priority**: Finish low HP enemies
- **Threat Assessment**: Focus high-attack enemies
- **Survival**: Defensive options when low HP
- **Crowd Control**: Value of stuns/silences
- **Cooldown Management**: Don't waste big skills on weak targets

## Project Structure

```
battle_advisor/
├── __init__.py           # Package init
├── game_state.py         # Battle state management (HP, skills, turns)
├── ai_advisor.py         # OpenAI integration for recommendations
├── battle_loader.py      # Load battles from logs or create samples
├── interactive_battle.py # Interactive CLI for turn-by-turn play
├── main.py               # Entry point with CLI arguments
└── README.md             # This file
```

## Example Session

```
==================================================
⚔️  AI BATTLE ADVISOR - Interactive Battle Simulation  ⚔️
==================================================

TURN 1
==================================================

🎯 Current Turn: Road Runner (enemy)
   HP: 100/100 (100%)

👤 PLAYER TEAM:
   ✅ Bugs Bunny: 156/156 HP | Effects: none
   ✅ Lola Bunny: 120/120 HP | Effects: none

👹 ENEMY TEAM:
   ⚔️ Wile E. Coyote: 140/140 HP | Effects: none
   ⚔️ Road Runner: 100/100 HP | Effects: none

👹 ENEMY TURN: Road Runner
   ⚡ Road Runner used Meep Meep!
   Target: Bugs Bunny
   💥 Dealt 23 damage!

[Press Enter to continue...]

TURN 1
==================================================

🎮 YOUR TURN: Bugs Bunny

📋 Available Skills:
  1. Safe Landing
     Type: single_target | Power: 100%
     Deal 100% damage to target enemy, gaining Attack Up...
  2. Befuddle (CD: 2)
     Type: single_target | Power: 130%
     Deal 130% damage to target enemy, inflicting Defense Down...

==================================================
🎯 AI RECOMMENDATION
==================================================
  Skill:  Befuddle
  Target: Wile E. Coyote

  💡 Reason: Wile E. Coyote has the highest attack and poses the 
     biggest threat. Befuddle deals high damage and applies Defense 
     Down + Silence, reducing his effectiveness.
==================================================

📌 Choose your action:
  [A] Accept AI recommendation
  [1-N] Choose skill by number
  [Q] Quit battle

Your choice: A

⚡ Bugs Bunny used Befuddle!
   Target: Wile E. Coyote
   💥 Dealt 58 damage!
   ✨ Effects: defense_down on Wile E. Coyote, silence on Wile E. Coyote
```

## Integration with Combat Analyzer

This project works alongside the Combat Analyzer:

| Feature | Combat Analyzer | Battle Advisor |
|---------|-----------------|----------------|
| When | Post-battle | During battle |
| Purpose | "Why did I lose?" | "What should I do?" |
| Output | Battle summary + suggestions | Skill recommendations |
| Data | Battle logs | Real-time state |

Both use:
- Same skill/character CSV data
- Same database connection
- Same OpenAI API

## Environment Variables

Requires `.env` file with:
```
OPENAI_API=your-api-key-here
DATABASE_URL=postgresql://...  # Optional, for character data
```
