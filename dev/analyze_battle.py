#!/usr/bin/env python3
"""
AI Combat Replay Summarizer - Quick Start Script
Run this script to analyze battle logs.

Usage:
    python analyze_battle.py                    # Analyze first available battle
    python analyze_battle.py --list             # List all battles
    python analyze_battle.py --battle 1         # Analyze battle #1
    python analyze_battle.py --interactive      # Interactive mode
    python analyze_battle.py --file <path>      # Analyze specific file
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from combat_analyzer.main import main

if __name__ == "__main__":
    main()
