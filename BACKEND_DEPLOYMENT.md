# Backend Deployment Guide

## Problem
The Streamlit frontend app is deployed on Streamlit Cloud, but it can't reach the FastAPI backend because:
- The app tries to connect to `http://127.0.0.1:8000` (local machine only)
- When deployed to Streamlit Cloud, there's no backend running at that address

## Solution: Deploy Your FastAPI Backend

You need to deploy the FastAPI backend to a cloud service. Here are the easiest options:

### **Option 1: Railway (Recommended - Easiest)**

1. **Create a Railway account** at https://railway.app
2. **Connect your GitHub repo**
3. **Create `railway.json` in your project root:**
```json
{
  "startCommand": "uvicorn app:app --host 0.0.0.0 --port 8000"
}
```
4. **Deploy** - Railway automatically detects FastAPI
5. **Copy the URL** from Railway dashboard (e.g., `https://your-app.railway.app`)

### **Option 2: Render (Free Tier Available)**

1. **Create account** at https://render.com
2. **New Web Service** → Connect GitHub repo
3. **Build & Start commands:**
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app:app --host 0.0.0.0 --port 8000`
4. **Deploy** and get your URL

### **Option 3: Fly.io**

Similar process, supports free tier.

---

## After Deploying Backend

### Step 1: Get Your Backend URL
After deployment, you'll get a URL like:
- `https://your-app.railway.app`
- `https://your-app.onrender.com`
- etc.

### Step 2: Update Streamlit Cloud Secrets

1. Go to **Streamlit Cloud Dashboard** → Your app
2. Click **Settings** → **Secrets**
3. Add this:
```toml
API_BASE_URL = "https://your-backend-url.com"
```

Replace `https://your-backend-url.com` with your actual backend URL.

### Step 3: Redeploy
Push your code changes (or just wait for auto-redeploy) and the app will use the new URL.

---

## Local Development

For local testing, the app automatically uses `http://127.0.0.1:8000`:
1. Run your FastAPI backend: `uvicorn app:app --reload`
2. Run Streamlit: `streamlit run app.py`
3. Everything works locally

---

## Configuration Priority

The app uses this priority for API URL:
1. **Environment variable** `API_BASE_URL` (if set in Streamlit Cloud secrets)
2. **Default**: `http://127.0.0.1:8000` (local development)

---

## Testing

After deployment, you can verify the connection works:
1. Open your Streamlit Cloud app
2. Select a location
3. If you see price predictions, the backend connection is working ✅
4. If you see "Connection refused", check:
   - Backend is deployed and running
   - `API_BASE_URL` is correctly set in Streamlit Cloud secrets
   - Backend URL is accessible (no firewall blocks)
