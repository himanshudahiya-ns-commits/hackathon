#!/usr/bin/env python3
"""
AI Combat Replay Summarizer - Main CLI
Analyzes battle logs and explains why battles were won/lost.
"""
import os
import sys
import json
import argparse
from pathlib import Path

from .battle_parser import parse_battle_log
from .metrics import compute_battle_metrics
from .llm_analyzer import BattleAnalyzer, build_battle_summary


def find_battle_logs(source_dir: str) -> list:
    """Find all battle log files in source directory."""
    logs = []
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"Error: Source directory not found: {source_dir}")
        return logs
    
    # Search for client_battle_log_*.txt files
    for data_dir in source_path.iterdir():
        if data_dir.is_dir() and data_dir.name.startswith("data"):
            for file in data_dir.iterdir():
                if file.name.startswith("client_battle_log_") and file.suffix == ".txt":
                    logs.append({
                        "path": str(file),
                        "name": data_dir.name,
                        "battle_id": file.stem.replace("client_battle_log_", "")
                    })
    
    return logs


def print_separator():
    """Print a visual separator."""
    print("\n" + "=" * 60 + "\n")


def print_metrics_summary(metrics):
    """Print a summary of battle metrics."""
    print("📊 BATTLE METRICS")
    print("-" * 40)
    print(f"Result: {'🏆 WIN' if metrics.result == 'WIN' else '💀 LOSS'}")
    print(f"Total Turns: {metrics.total_turns}")
    print(f"Stars: {'⭐' * metrics.stars if metrics.stars > 0 else 'N/A'}")
    
    print("\n👤 PLAYER TEAM (LEFT)")
    print(f"  Characters: {metrics.player_team.character_count}")
    print(f"  Avg Attack: {metrics.player_team.avg_attack:.1f}")
    print(f"  Avg Defense: {metrics.player_team.avg_defense:.1f}")
    print(f"  Avg Speed: {metrics.player_team.avg_speed:.1f}")
    print(f"  Total Damage Dealt: {metrics.player_team.total_damage_dealt}")
    print(f"  Characters Alive: {metrics.player_team.characters_alive}/{metrics.player_team.character_count}")
    
    print("\n👹 ENEMY TEAM (RIGHT)")
    print(f"  Characters: {metrics.enemy_team.character_count}")
    print(f"  Avg Attack: {metrics.enemy_team.avg_attack:.1f}")
    print(f"  Avg Defense: {metrics.enemy_team.avg_defense:.1f}")
    print(f"  Avg Speed: {metrics.enemy_team.avg_speed:.1f}")
    print(f"  Total Damage Dealt: {metrics.enemy_team.total_damage_dealt}")
    print(f"  Characters Alive: {metrics.enemy_team.characters_alive}/{metrics.enemy_team.character_count}")
    
    print("\n⚔️ STAT ADVANTAGES")
    print(f"  Speed: {metrics.speed_advantage}")
    print(f"  Attack: {metrics.attack_advantage}")
    print(f"  Defense: {metrics.defense_advantage}")
    print(f"  Health: {metrics.health_advantage}")
    
    if metrics.first_ko:
        print(f"\n💀 First KO: {metrics.first_ko['character']} on turn {metrics.first_ko['turn']}")
    
    if metrics.biggest_hit:
        print(f"💥 Biggest Hit: {metrics.biggest_hit['damage']} damage by {metrics.biggest_hit['attacker']}")


def analyze_single_battle(log_path: str, show_metrics: bool = True, show_json: bool = False):
    """Analyze a single battle log."""
    print(f"📁 Analyzing: {log_path}")
    print_separator()
    
    try:
        # Parse the battle log
        print("🔍 Parsing battle log...")
        battle = parse_battle_log(log_path)
        
        # Compute metrics
        print("📊 Computing metrics...")
        metrics = compute_battle_metrics(battle)
        
        if show_metrics:
            print_metrics_summary(metrics)
            print_separator()
        
        if show_json:
            summary = build_battle_summary(metrics)
            print("📋 JSON SUMMARY")
            print("-" * 40)
            print(json.dumps(summary, indent=2))
            print_separator()
        
        # Analyze with LLM
        print("🤖 Generating AI Analysis...")
        print("-" * 40)
        
        analyzer = BattleAnalyzer()
        analysis = analyzer.analyze(metrics)
        
        print(analysis)
        print_separator()
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Error: File not found: {log_path}")
        return False
    except Exception as e:
        print(f"❌ Error analyzing battle: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def list_available_battles(source_dir: str):
    """List all available battle logs."""
    logs = find_battle_logs(source_dir)
    
    if not logs:
        print(f"No battle logs found in {source_dir}")
        return
    
    print(f"📂 Found {len(logs)} battle logs in {source_dir}:\n")
    for i, log in enumerate(logs, 1):
        print(f"  {i}. [{log['name']}] {log['battle_id'][:20]}...")
    
    print(f"\nUse --battle <number> to analyze a specific battle")
    print(f"Or use --file <path> to analyze a specific file")


def interactive_mode(source_dir: str):
    """Run in interactive mode."""
    logs = find_battle_logs(source_dir)
    
    if not logs:
        print(f"No battle logs found in {source_dir}")
        return
    
    while True:
        print("\n" + "=" * 60)
        print("🎮 AI COMBAT REPLAY SUMMARIZER")
        print("=" * 60)
        print(f"\nFound {len(logs)} battles:\n")
        
        for i, log in enumerate(logs, 1):
            print(f"  {i}. [{log['name']}] Battle {log['battle_id'][:16]}...")
        
        print(f"\n  0. Exit")
        
        try:
            choice = input("\nSelect a battle to analyze (0-{0}): ".format(len(logs)))
            choice = int(choice)
            
            if choice == 0:
                print("Goodbye! 👋")
                break
            
            if 1 <= choice <= len(logs):
                analyze_single_battle(logs[choice - 1]["path"])
            else:
                print("Invalid choice. Please try again.")
                
        except ValueError:
            print("Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nGoodbye! 👋")
            break


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="AI Combat Replay Summarizer - Analyze battle logs and explain outcomes"
    )
    
    parser.add_argument(
        "--source", "-s",
        default="/Users/himanshu.dahiya/Desktop/data/sourse",
        help="Source directory containing battle data folders (default: /Users/himanshu.dahiya/Desktop/data/sourse)"
    )
    
    parser.add_argument(
        "--file", "-f",
        help="Analyze a specific battle log file"
    )
    
    parser.add_argument(
        "--battle", "-b",
        type=int,
        help="Analyze battle by number (use --list to see available battles)"
    )
    
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available battle logs"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode"
    )
    
    parser.add_argument(
        "--metrics", "-m",
        action="store_true",
        default=True,
        help="Show detailed metrics (default: True)"
    )
    
    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Show JSON summary sent to LLM"
    )
    
    parser.add_argument(
        "--no-metrics",
        action="store_true",
        help="Hide detailed metrics"
    )
    
    args = parser.parse_args()
    
    # Handle --no-metrics flag
    show_metrics = not args.no_metrics
    
    if args.list:
        list_available_battles(args.source)
    elif args.file:
        analyze_single_battle(args.file, show_metrics=show_metrics, show_json=args.json)
    elif args.battle:
        logs = find_battle_logs(args.source)
        if 1 <= args.battle <= len(logs):
            analyze_single_battle(logs[args.battle - 1]["path"], show_metrics=show_metrics, show_json=args.json)
        else:
            print(f"Invalid battle number. Use --list to see available battles (1-{len(logs)})")
    elif args.interactive:
        interactive_mode(args.source)
    else:
        # Default: analyze first available battle or show help
        logs = find_battle_logs(args.source)
        if logs:
            print("🎮 AI COMBAT REPLAY SUMMARIZER")
            print("=" * 60)
            print(f"\nFound {len(logs)} battles. Analyzing the first one...\n")
            analyze_single_battle(logs[0]["path"], show_metrics=show_metrics, show_json=args.json)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
