#!/usr/bin/env python
"""
Main entry point for the Fashion Recommendation System
"""

from app.app import app

if __name__ == '__main__':
    print("="*60)
    print("Starting 🧣 FabricJi ✨ Fashion Recommendation System")
    print("="*60)
    print("\nServer running at: http://127.0.0.1:5000")
    print("Press CTRL+C to quit\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)