import sys
import os

# Add the project root to sys.path so we can import the web package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.app import app

# Vercel looks for the 'app' variable by default in api/index.py
# If you need to export it with a different name, you can do so here.
