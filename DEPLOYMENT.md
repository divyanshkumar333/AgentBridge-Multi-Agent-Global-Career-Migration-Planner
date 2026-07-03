# AgentBridge Deployment Guide

This guide details the step-by-step instructions required to deploy the AgentBridge prototype to production. The setup is configured for a split deployment:
1. **Backend**: FastAPI app hosted on **Render**.
2. **Frontend**: Static files hosted on **Vercel** with a secure API request proxy.

---

## 🛠️ Step 1: Backend Deployment on Render

Render will host the FastAPI service and serve the SQLite database.

### Manual Web Service Setup (Recommended - 100% Free)
Deploying manually on Render is completely free and does not require entering any credit card/payment details.

1. Sign in to the [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Web Service**.
3. Connect your GitHub repository.
4. Configure the following settings:
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Expand the **Advanced** section and add the following **Environment Variables**:
   - `NVIDIA_API_KEY`: *your_nvidia_nim_api_key*
   - `GEMINI_API_KEY`: *your_gemini_api_key*
6. Click **Create Web Service**.

---

### (Alternative) Blueprint Deploy (Requires Card on File)
Render requires credit card details on file to deploy via Blueprints, even if using the free tier:
1. Click **New +** and select **Blueprint**.
2. Connect your GitHub repository.
3. Render will automatically detect `render.yaml` and configure a Web Service named `agentbridge-backend`.
4. Enter your payment details, set environment variables, and click **Approve**.

Once deployed, note down the provided Render service URL (e.g., `https://agentbridge-backend.onrender.com`).

---

## 🌐 Step 2: Frontend Deployment on Vercel

Vercel will host the static frontend pages and route API requests through a secure proxy rewrite.

1. Open [vercel.json](vercel.json) in your repository root.
2. Update the `destination` URL of the `/api/:path*` rewrite route to point to your deployed Render URL:
   ```json
   "rewrites": [
     {
       "source": "/api/:path*",
       "destination": "https://<your-render-backend-url>/api/:path*"
     }
   ]
   ```
3. Save the changes.
4. Sign in to the [Vercel Dashboard](https://vercel.com/) and click **Add New** -> **Project**.
5. Import your repository.
6. Leave the build configurations as default (Vercel will auto-detect the root directory and use the `vercel.json` rules).
7. Click **Deploy**.

---

## 🔒 Step 3: Environment Variables Summary

Ensure both backend API keys are supplied on your Render service:

| Variable | Description | Source |
| :--- | :--- | :--- |
| `NVIDIA_API_KEY` | Required for the Profiler Agent (Meta Llama-3.3-70b NIM model). | [NVIDIA NIM Portal](https://build.nvidia.com/) |
| `GEMINI_API_KEY` | Required for Gemini Agent collaboration pipelines. | [Google AI Studio](https://aistudio.google.com/) |
