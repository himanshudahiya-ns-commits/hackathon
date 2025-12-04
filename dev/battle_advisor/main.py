"""
AI Battle Advisor - Main Entry Point
Run interactive battles with AI skill recommendations.
"""
import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from battle_advisor.interactive_battle import InteractiveBattle, run_sample_battle
from battle_advisor.battle_loader import get_battle_loader
from battle_advisor.ai_advisor import get_ai_advisor


def find_battle_logs(base_dir: str = None) -> list:
    """Find all battle log files."""
    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent / "sourse"
    else:
        base_dir = Path(base_dir)
    
    logs = []
    if base_dir.exists():
        for log_file in base_dir.rglob("client_battle_log_*.txt"):
            logs.append(str(log_file))
    
    return sorted(logs)


def list_battles():
    """List available battle logs."""
    logs = find_battle_logs()
    
    if not logs:
        print("No battle logs found.")
        return
    
    print("\n📁 Available Battle Logs:")
    print("-" * 60)
    for i, log in enumerate(logs, 1):
        # Extract folder name
        folder = Path(log).parent.name
        filename = Path(log).name[:50] + "..."
        print(f"  {i}. [{folder}] {filename}")
    print("-" * 60)
    print(f"Total: {len(logs)} battles")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Battle Advisor - Turn-by-turn skill recommendations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m battle_advisor.main                    # Run sample battle
  python -m battle_advisor.main --list             # List available battles
  python -m battle_advisor.main --battle 1         # Run battle #1 from logs
  python -m battle_advisor.main --sample           # Run sample battle
  python -m battle_advisor.main --file <path>      # Run specific battle log
        """
    )
    
    parser.add_argument("--list", action="store_true", 
                        help="List available battle logs")
    parser.add_argument("--battle", type=int, 
                        help="Battle number to run (from --list)")
    parser.add_argument("--file", type=str, 
                        help="Path to specific battle log file")
    parser.add_argument("--sample", action="store_true", 
                        help="Run sample battle (default)")
    parser.add_argument("--no-ai", action="store_true",
                        help="Disable AI recommendations")
    
    args = parser.parse_args()
    
    # List battles
    if args.list:
        list_battles()
        return
    
    # Check AI availability
    ai_advisor = None
    if not args.no_ai:
        ai_advisor = get_ai_advisor()
        if ai_advisor:
            print("✅ AI Advisor loaded successfully")
        else:
            print("⚠️  AI Advisor not available (check OPENAI_API in .env)")
    
    # Load battle
    loader = get_battle_loader()
    game_state = None
    
    if args.file:
        # Load from specific file
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}")
            return
        print(f"📁 Loading battle from: {args.file}")
        game_state = loader.load_from_battle_log(args.file)
        
    elif args.battle:
        # Load from battle number
        logs = find_battle_logs()
        if not logs:
            print("No battle logs found.")
            return
        if args.battle < 1 or args.battle > len(logs):
            print(f"Invalid battle number. Choose 1-{len(logs)}")
            return
        log_path = logs[args.battle - 1]
        print(f"📁 Loading battle from: {log_path}")
        game_state = loader.load_from_battle_log(log_path)
        
    else:
        # Default: sample battle
        print("🎮 Starting sample battle...")
        game_state = loader.create_sample_battle()
    
    # Run interactive battle
    if game_state:
        battle = InteractiveBattle(game_state, ai_advisor)
        battle.run()
    else:
        print("Failed to load battle state.")


if __name__ == "__main__":
    main()
