# 🚀 Sentinel Core - Deployment Guide

## Architecture Overview

```
┌─────────────────────────┐     ┌─────────────────────────┐
│   Vercel (Frontend)     │────▶│   Railway (Backend)     │
│                         │     │                         │
│ sentinel-core-sigma     │     │   FastAPI + Gemini AI   │
│      .vercel.app        │     │                         │
└─────────────────────────┘     └─────────────────────────┘
                                          │
                                          ▼
                                ┌─────────────────────────┐
                                │      Supabase           │
                                │   (Auth + Database)     │
                                └─────────────────────────┘
```

---

## 📋 Step 1: Deploy Backend to Railway

### Option A: Railway CLI (Recommended)

1. **Install Railway CLI:**
   ```powershell
   npm install -g @railway/cli
   ```

2. **Login to Railway:**
   ```powershell
   railway login
   ```

3. **Navigate to backend folder:**
   ```powershell
   cd "c:\Users\yashw\Downloads\sentinel legal\backend"
   ```

4. **Initialize Railway project:**
   ```powershell
   railway init
   ```
   - Choose "Empty Project"
   - Name it: `sentinel-core-backend`

5. **Add environment variables:**
   ```powershell
   railway variables set GEMINI_API_KEY=your_gemini_api_key
   railway variables set DEBUG=false
   ```

6. **Deploy:**
   ```powershell
   railway up
   ```

7. **Get your Railway URL:**
   ```powershell
   railway domain
   ```
   This will generate a URL like: `https://sentinel-core-backend-production.up.railway.app`

---

### Option B: Railway Dashboard (No CLI)

1. Go to **https://railway.app**
2. Sign up / Log in with GitHub
3. Click **"New Project"**
4. Choose **"Deploy from GitHub repo"**
5. Select your repository or **"Empty Project"**
6. If empty project:
   - Click **"Add a service"** → **"GitHub Repo"**
   - Connect your repo and select `backend` folder
   OR
   - **Drag and drop** the `backend` folder

7. **Add environment variables** in Dashboard:
   - `GEMINI_API_KEY` = your key
   - `DEBUG` = false

8. Click **"Deploy"**

9. Go to **Settings** → **Networking** → Click **"Generate Domain"**

---

## 📋 Step 2: Update Frontend with Railway URL

After getting your Railway URL (e.g., `https://sentinel-core-backend.up.railway.app`), update the frontend:

Edit `frontend/index.html` around **line 61**:

```javascript
// Change this line:
var API_BASE_URL = window.location.hostname === 'localhost' ? '' : '';

// To this (replace with YOUR Railway URL):
var API_BASE_URL = window.location.hostname === 'localhost' ? '' : 'https://your-railway-url.up.railway.app';
```

---

## 📋 Step 3: Redeploy Frontend to Vercel

```powershell
cd "c:\Users\yashw\Downloads\sentinel legal"
vercel --prod --yes
```

---

## ✅ Testing

1. **Test Backend Health:**
   ```powershell
   curl https://your-railway-url.up.railway.app/api/v1/health
   ```

2. **Test Full Flow:**
   - Go to https://sentinel-core-sigma.vercel.app
   - Sign in with Supabase
   - Upload a contract PDF
   - View analysis results!

---

## 🔧 Troubleshooting

### Backend not starting?
- Check Railway logs: `railway logs`
- Verify GEMINI_API_KEY is set correctly

### CORS errors?
- Backend already allows all origins with `allow_origins=["*"]`
- If issues persist, check browser console for specific errors

### API calls failing on Vercel?
- Ensure `API_BASE_URL` in frontend is correctly set to Railway URL
- Redeploy with `vercel --prod --yes`

---

## 📊 Environment Variables Reference

### Railway Backend:
| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | Google Gemini API key |
| `DEBUG` | No | Set to `false` for production |

### Vercel Frontend (already set):
| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous key |

---

## 🎉 You're Done!

Your Sentinel Core platform should now be fully deployed:
- **Frontend**: https://sentinel-core-sigma.vercel.app
- **Backend**: https://your-railway-url.up.railway.app
- **API Docs**: https://your-railway-url.up.railway.app/docs
