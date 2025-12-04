#!/usr/bin/env python3
"""
AI Battle Advisor - Quick Start Script
Run this to start an interactive battle with AI skill recommendations.

Usage:
    python run_battle_advisor.py                # Run sample battle
    python run_battle_advisor.py --list         # List available battles
    python run_battle_advisor.py --battle 1     # Run battle #1
    python run_battle_advisor.py --sample       # Run sample battle
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from battle_advisor.main import main

if __name__ == "__main__":
    main()
