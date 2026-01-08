# Systematic Review Tool (Two-stage screening)

A lightweight Flask + SQLite app to run:
1) Title & abstract screening
2) Full-text screening

## Quick start

1) Before you begin, open a terminal:

- **Windows:** PowerShell  
- **macOS:** Terminal  
- **Linux:** Your default terminal app (e.g., GNOME Terminal, Konsole)

2) Then navigate to the project folder: 

```bash
# Windows:
cd C:\path\to\project
# macOS/Linux:
cd /path/to/project
```

> Tip: If your path contains spaces, wrap it in quotes:
> - Example (Windows): cd "C:\path\to project"
> - Example (macOS/Linux): cd "/path/to project"

3) Enter these commands in the terminal
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

4) Open:
- http://127.0.0.1:5000/0_home.html

The SQLite database is created automatically at `instance/review.db`.

## Import formats

- [Web of Science](https://www.webofscience.com/wos/alldb/basic-search): `.xls`
- [Scopus](https://www.scopus.com/pages/home#basic): `.csv`

Example files are included in `examples/`.
