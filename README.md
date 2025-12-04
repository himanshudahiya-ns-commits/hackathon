# AI Battle Tools (Battle Advisor + Combat Analyzer)

Two complementary tools for Looney Tunes: World of Mayhem:

- AI Battle Advisor: Interactive, turn-by-turn skill recommendations while you “play back” a battle.
- AI Combat Replay Summarizer: Post-battle analysis that explains why a fight was won/lost and suggests improvements.

## Repository Structure

```
.
├── .gitignore                 # Ignore rules for secrets, venv, caches, etc.
├── characters.json            # Character-to-skill mapping and presence in sample datasets
├── dev/                       # Source code (entry scripts + 2 Python packages)
│   ├── run_battle_advisor.py  # Quick-start entry for interactive advisor
│   ├── analyze_battle.py      # Quick-start entry for analyzer
│   ├── battle_advisor/        # Advisor package (AI recs, state, loader, UI)
│   └── combat_analyzer/       # Analyzer package (parser, metrics, LLM)
└── sourse/                    # Data assets (CSV metadata + sample battle logs)
    ├── [LT] Toon Kits - _DATABASE.csv
    ├── [LT] Toon Kits - _SKILLS SUMMARY.csv
    └── data{1..4}/            # Battle-Parameters/Result + client_battle_log_*.txt
```

## Quick Start

1) Python environment

```bash
python3 -m venv venv
source venv/bin/activate           # Windows: venv\Scripts\activate
pip install -r dev/combat_analyzer/requirements.txt
# If needed, also ensure:
pip install openai python-dotenv
```

2) Environment variables

Create a `.env` file (in project root or `dev/`):

```
OPENAI_API=your-openai-key
# Optional for DB-enriched analysis
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

3) Run the Battle Advisor (interactive)

```bash
cd dev
python run_battle_advisor.py           # Sample battle
python run_battle_advisor.py --list    # List available logs (from sourse/)
python run_battle_advisor.py --battle 1
python run_battle_advisor.py --file path/to/client_battle_log_xxx.txt
python run_battle_advisor.py --no-ai   # Manual mode
```

4) Run the Combat Analyzer (post-battle)

```bash
cd dev
python analyze_battle.py                  # Analyze first available battle
python analyze_battle.py --list           # List all logs
python analyze_battle.py --battle 1       # Analyze Nth log
python analyze_battle.py --file /abs/path/to/client_battle_log_xxx.txt
python analyze_battle.py --interactive    # Menu-driven
python analyze_battle.py --json           # Print JSON sent to LLM
python analyze_battle.py --no-metrics     # Hide metrics section
```

## What Each Part Does

- dev/battle_advisor/
  - game_state.py: Simulates teams, skills, effects, turns.
  - ai_advisor.py: Calls OpenAI to recommend best skill/target.
  - battle_loader.py: Builds a playable state from logs or sample data.
  - interactive_battle.py: CLI loop for step-by-step play.
  - main.py: CLI args and wiring.

- dev/combat_analyzer/
  - battle_parser.py: Parses raw `client_battle_log_*.txt` files.
  - metrics.py: Computes damage, KO, speed/attack/defense/health advantages, moments.
  - llm_analyzer.py: Builds LLM prompt with metrics and optional DB/CSV context.
  - db_helper.py: Optional PostgreSQL integration for richer character info.
  - csv_helper.py: Reads character/skill metadata from `sourse/` CSVs.
  - main.py: CLI entry.

- sourse/
  - CSVs with character and skill metadata.
  - data1..data4 with sample logs and results to test both tools quickly.

- characters.json
  - Handy mapping of notable characters to skills and which data folders they appear in.

## Notes

- OpenAI usage can incur costs; keep an eye on your API key and model choice.
- If you don’t have a PostgreSQL DB, the analyzer will still work using CSV data.
- `.gitignore` already excludes common secrets (`.env`), caches, and virtual environments.

## License

Add your preferred license here (e.g., MIT) if you plan to share publicly.
