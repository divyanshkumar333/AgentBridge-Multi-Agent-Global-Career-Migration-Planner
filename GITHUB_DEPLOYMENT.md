# 🚀 Deploying AgentBridge Using GitHub & Free Services

This guide provides step-by-step instructions to deploy both the **FastAPI Backend** and the **Static HTML/CSS/JS Frontend** of AgentBridge using free services.

## 🏗️ Architecture Overview
Because GitHub does not host dynamic runtime backends (like FastAPI/Python), we deploy in a split configuration:
1. **Frontend**: Hosted for free on **GitHub Pages**.
2. **Backend**: Hosted for free on **Render** (or Koyeb).
3. **Automation**: **GitHub Actions** builds and deploys the frontend from the `./frontend` directory automatically on every push.

---

## 🛠️ Step 1: Deploy the Backend on Render (Free Tier)
Render offers a free tier for web services and integrates seamlessly with GitHub.

1. Sign in to the [Render Dashboard](https://dashboard.render.com/) (you can log in using your GitHub account).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository.
4. Configure the following settings:
   - **Name**: `agentbridge-backend`
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Click **Advanced** and add the following **Environment Variables**:
   - `NVIDIA_API_KEY`: *Your NVIDIA NIM API key* (obtained from [NVIDIA NIM Portal](https://build.nvidia.com/))
   - `GEMINI_API_KEY`: *Your Gemini API key* (obtained from [Google AI Studio](https://aistudio.google.com/))
6. Click **Create Web Service**.

Once deployed, copy your Render Web Service URL (e.g., `https://agentbridge-backend.onrender.com`).

---

## 🌐 Step 2: Configure the API Base URL in your Repository
To connect your GitHub Pages frontend to your Render backend, update the API configuration:

1. Open the [frontend/app.js](file:///c:/Users/acer/.gemini/antigravity-ide/scratch/AgentBridge%20Multi-Agent%20Global%20Career%20&%20Migration%20Planner/frontend/app.js) file.
2. Locate the `API_BASE` variable at the top of the file:
   ```javascript
   const API_BASE = "";
   ```
3. Update it with your live Render URL:
   ```javascript
   const API_BASE = "https://agentbridge-backend.onrender.com"; // Replace with your actual Render URL
   ```
4. Save the file, commit, and push the change to your GitHub repository:
   ```bash
   git add frontend/app.js
   git commit -m "Configure API_BASE for production"
   git push origin main
   ```

---

## ⚡ Step 3: Deploy the Frontend to GitHub Pages
We use **GitHub Actions** to publish only the `frontend/` directory to GitHub Pages.

1. A workflow file has been created at [.github/workflows/deploy-frontend.yml](file:///c:/Users/acer/.gemini/antigravity-ide/scratch/AgentBridge%20Multi-Agent%20Global%20Career%20&%20Migration%20Planner/.github/workflows/deploy-frontend.yml).
2. Push this workflow to your repository:
   ```bash
   git add .github/workflows/deploy-frontend.yml
   git commit -m "Add GitHub Pages deployment workflow"
   git push origin main
   ```
3. Go to your repository on GitHub.
4. Navigate to **Settings** -> **Actions** -> **General**. Under **Workflow permissions**, select **Read and write permissions** and click **Save**.
5. Push a new change, or go to the **Actions** tab on GitHub, select **Deploy Frontend to GitHub Pages**, and click **Run workflow** manually.
6. Once the workflow completes, a new branch named `gh-pages` will be created automatically.
7. Go to **Settings** -> **Pages** in your GitHub repository.
8. Under **Build and deployment**:
   - **Source**: Select `Deploy from a branch`.
   - **Branch**: Select `gh-pages` and `/ (root)`.
   - Click **Save**.

Your frontend is now live at: `https://<your-github-username>.github.io/<your-repo-name>/`!

---

## 🔒 Security & Free Tier Maintenance
- **Render Spin-Up Delay**: Free-tier web services on Render spin down after 15 minutes of inactivity. When you first visit your site or submit a profile, the first request may take up to 50 seconds to complete while the backend spins back up.
- **GitHub Secrets**: Never hardcode your API keys (`NVIDIA_API_KEY` or `GEMINI_API_KEY`) in the source code or commit them. Always keep them in the Render environment configuration.
