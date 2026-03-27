# IPL Fantasy 2026 — Chotu vs Dhakan 🏏

## Setup Instructions

### 1. Deploy API to Render
1. Go to render.com → New → Web Service
2. Connect this GitHub repo
3. Set **Root Directory** to `api`
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `gunicorn app:app --bind 0.0.0.0:10000`
6. Click Deploy
7. Copy your Render URL (e.g. `https://ipl-fantasy-api.onrender.com`)

### 2. Update API URL in app
1. Open `index.html`
2. Find line: `const API_URL = "RENDER_URL_HERE";`
3. Replace with your Render URL
4. Commit and push

### 3. Enable GitHub Pages
1. Go to repo Settings → Pages
2. Source: Deploy from branch → main → / (root)
3. Your app will be live at: `https://gargvaibhav02.github.io/ipl-fantasy`

## How to use
1. Open the app link
2. Click a match → enter 7+7 players + scorecard URL
3. Tap ⚡ Calculate Scores
4. Review breakdown → Save!
