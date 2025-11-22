# Spell Recorder (Streamlit)

Collect microphone recordings for Harry Potter spells and store them in MongoDB for training a classifier.

**Spells collected:** Lumos, Nox, Alohomora, Wingardium Leviosa, Accio, Reparo

## Quick Start (Local)

```powershell
cd "d:\harry potter charm collection"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements_streamlit.txt
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

## MongoDB Configuration

The app uses environment variables for MongoDB connection. Create a `.env` file in the project root:

```
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/?appName=YourApp
MONGO_DB=spells
MONGO_BUCKET=fs
```

Or set them in PowerShell before running:
```powershell
$env:MONGO_URI = "mongodb+srv://user:pass@..."
$env:MONGO_DB = "spells"
$env:MONGO_BUCKET = "fs"
streamlit run streamlit_app.py
```

## Deploy to Streamlit Cloud

1. Push your code to GitHub (ensure `.env` is in `.gitignore`)
2. Go to https://share.streamlit.io/
3. Click "New app"
4. Select your repo and set:
   - Main file: `streamlit_app.py`
   - Python version: 3.10 or higher
5. Click "Advanced settings" → "Secrets" and add:
```toml
MONGO_URI = "mongodb+srv://user:pass@cluster.mongodb.net/?appName=YourApp"
MONGO_DB = "spells"
MONGO_BUCKET = "fs"
```
6. Deploy

## Admin Tools (Local)

Use `admin_db.py` to manage your MongoDB recordings:

```powershell
# View counts
python admin_db.py counts --by-username

# List recent recordings
python admin_db.py list --limit 50

# Export to local folder
python admin_db.py export --outdir exports --csv metadata.csv

# Check configuration
python admin_db.py debug
```

## Features

- Upload audio files for each spell (WAV, MP3, OGG, FLAC, M4A)
- Automatic resampling to 16 kHz mono
- Stores in MongoDB GridFS with metadata
- Counter showing selected spells
- Sanitized usernames for safe storage

## Privacy

- Only collect voices with consent
- Inform contributors how audio will be used
- Don't collect sensitive information in usernames
