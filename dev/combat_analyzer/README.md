# AI Combat Replay Summarizer

Analyzes battle logs from Looney Tunes: World of Mayhem and provides AI-powered explanations of battle outcomes.

## Features

- **Battle Log Parser**: Extracts structured data from raw battle logs
- **Metrics Computation**: Calculates damage, healing, KOs, turn order, stat advantages
- **Database Integration**: Fetches character info (rarity, archetype, base stats, themes) from PostgreSQL
- **AI Analysis**: Uses OpenAI GPT to explain why battles were won/lost with rich context
- **Actionable Suggestions**: Provides tips for improvement based on character data

## Setup

```bash
# Navigate to dev folder
cd /Users/himanshu.dahiya/Desktop/data/dev

# Activate virtual environment (already created)
source venv/bin/activate

# Install dependencies (if not already installed)
pip install -r combat_analyzer/requirements.txt
```

## Usage

```bash
# Analyze first available battle
python analyze_battle.py

# List all available battles
python analyze_battle.py --list

# Analyze a specific battle by number
python analyze_battle.py --battle 1

# Analyze a specific file
python analyze_battle.py --file /path/to/client_battle_log_xxx.txt

# Interactive mode
python analyze_battle.py --interactive

# Show JSON summary (for debugging)
python analyze_battle.py --json

# Hide detailed metrics
python analyze_battle.py --no-metrics
```

## Project Structure

```
combat_analyzer/
├── __init__.py          # Package init
├── battle_parser.py     # Parses raw battle log text files
├── metrics.py           # Computes battle metrics
├── db_helper.py         # Database integration for character data
├── llm_analyzer.py      # OpenAI API integration
├── main.py              # CLI interface
└── requirements.txt     # Dependencies
```

## How It Works

1. **Parse**: Read battle log and extract teams, stats, events
2. **Compute**: Calculate metrics (damage, KOs, turn order, advantages)
3. **Summarize**: Build structured JSON for the LLM
4. **Analyze**: Send to OpenAI API for human-readable explanation

## Environment Variables

Create a `.env` file in the `dev` folder with:

```
OPENAI_API=your-api-key-here

# Database connection (PostgreSQL)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=looney_tunes
DB_USER=postgres
DB_PASSWORD=your_password_here
```

## Database Schema

The system uses 3 PostgreSQL tables:

### characters
- `character` (VARCHAR) - Character ID
- `rarity`, `archetype`, `region`, `theme`, `family`, `race`
- `battle_tier`, `boss`, `collectable`, `original`
- Various tags for matching

### names_descriptions
- `character_id` (VARCHAR) - Links to characters
- `name` - Display name
- `description` - Character description

### stats_analysis
- `character_name` (VARCHAR) - Links to names_descriptions
- `attack`, `defense`, `health`, `speed` - Base stats
- `pct_to_avg` - Percentage compared to average

## Output Example

```
📊 BATTLE METRICS
----------------------------------------
Result: 🏆 WIN
Total Turns: 6
Stars: ⭐⭐⭐

👤 PLAYER TEAM (LEFT)
  Characters: 1
  Avg Attack: 40.0
  Total Damage Dealt: 158
  Characters Alive: 1/1

👹 ENEMY TEAM (RIGHT)
  Characters: 2
  Avg Attack: 63.5
  Total Damage Dealt: 140
  Characters Alive: 0/2

🤖 AI ANALYSIS
----------------------------------------
## Battle Summary
The player won a close 1v2 battle with Bugs Bunny against Wile E. Coyote 
and Road Runner. Despite being outnumbered, Bugs survived with 16 HP...

## Key Factors
- Speed advantage allowed Bugs to act first
- Attack Down debuffs reduced enemy damage output
- Focused targeting eliminated Road Runner early

## Suggestions
- Consider adding a second character for safer battles
- Upgrade Bugs Bunny's defense to take less damage
- Maintain the debuff strategy - it's working well
```

## Future Enhancements

- [ ] Skill metadata integration (skill names, descriptions)
- [ ] Character stat rankings (vs average, vs max)
- [ ] Web UI dashboard
- [ ] Batch analysis of multiple battles
- [ ] Export reports to PDF/HTML
