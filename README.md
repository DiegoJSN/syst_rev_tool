# Systematic Review Tool (Two-stage screening)

A lightweight Flask + SQLite app to run:
1) Title & abstract screening
2) Full-text screening

## Quick start

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open:
- http://127.0.0.1:5000/0_home.html

The SQLite database is created automatically at `instance/review.db`.

## Import formats

- Web of Science: `.xls`
- Scopus: `.csv`

Example files are included in `examples/`.
