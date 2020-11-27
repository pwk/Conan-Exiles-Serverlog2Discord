# Conan-Exiles-Serverlog2Discord
Conan Exiles Serverlog to Discord via webhook and sqlite3 database

**Following informations are logged:**
- chat
- new players (with funcomid)
- players joining server (with steamid and ip)
- players leaving server
- gameworld is loaded
- server is shutdown
- server crashes (with error message)

**What do you need?**
- Only python3 (https://www.python.org/downloads/)

**Following modules are required:** (standard only)
- subprocess re, time, requests, json, sqlite3, os, datetime, configparser

**Installation:**
1) Download all files and save them in any folder
2) Edit config.ini and enter your data
3) To start the script open start.py
