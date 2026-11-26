# Running and deploying Decision Room

The app is a single Streamlit process. The calculation engine (`engine/`) is separate from the interface (`app/`).

## A. Classroom presentation (safest, no internet needed)
1. Install the dependencies once: `python -m pip install -r requirements.txt`
2. Double-click `run.bat` (or run `python -m streamlit run app/main.py`).
3. Open http://localhost:8501 and connect the laptop to the projector.

Calculations, charts and the whole interface work fully offline. The AI assistant needs internet and an API key.
The IBM Plex and Newsreader fonts are downloaded from Google Fonts when online; otherwise system fonts are used.

## B. Free online: Streamlit Community Cloud
1. Upload this folder to a GitHub repository (private is fine). `.env` and `storage/` are already in `.gitignore`; keep them there.
2. On share.streamlit.io choose the repository, the branch and the main file `app/main.py`.
3. Under Advanced settings choose Python 3.11, then fill in Secrets (optional, for the AI features):
   ```toml
   GOOGLE_API_KEY = "your-key"
   OPENROUTER_API_KEY = "your-key"
   LLM_PROVIDER = "gemini"
   ```
4. Deploy. The public link opens on anyone's phone or laptop in the room.

Notes:
- A free app goes to sleep when it is not opened for a while. Open the link 5 minutes before the presentation.
- The server disk is temporary: sessions, runs and saved AI reports kept on the server disappear on restart. Use **Download session (JSON)** in the sidebar when you need to keep a case.
- API keys typed in the sidebar live only in that browser session and are never written to the server.

## C. Docker (Render, Railway, Hugging Face Spaces, VPS)
```bash
docker build -t decision-room .
docker run -p 8501:8501 --env-file .env decision-room
```
Platforms that provide a `PORT` variable are supported automatically. `.env` is not copied into the image (`.dockerignore`); set the keys through the platform's environment settings.

## AI engines and free quotas
- **Gemini 4 Hydrogen** (thinking level `low`). The free tier allows about 20 requests per day per project and model.
- **OpenRouter free models above 29B parameters.** A free account allows about 50 requests per day and 20 per minute.
- When the selected engine fails (quota, rate limit, outage), the next engine answers automatically and the report says who answered and why.
  A 429 (quota or rate limit) is never retried, so no quota is wasted on retries.
- Finished reports are saved with the run (`storage/runs/<run_id>/analysis_<engine>.json`), so reopening a report costs no request.

## Tests
```bash
python -m pytest tests -q
```
The tests cover the calculation engine (golden numbers), case editing, the LLM layer (without calling a real API) and the interface (AppTest).

## Security
- Never commit or share `.env`. If it was ever uploaded to a public place, regenerate the keys.
- Every text that comes from data (product names, session titles) is escaped before it enters HTML, including sessions from uploaded JSON files.
