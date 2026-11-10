# Deploying DataPilot to Render (Option 1 Guide)

This guide provides end-to-end instructions for deploying **DataPilot** to [Render](https://render.com) (or similar container platforms like Railway, Fly.io, Google Cloud Run) using the single-container architecture.

---

## 🌟 Why Option 1 on Render?

- **Unified Single-Port Serving**: The multi-stage Docker build bundles the compiled React 19 SPA directly into FastAPI. A single container serves the web frontend, Swagger API docs (`/docs`), and all analytical endpoints on port `8000` (or Render's `$PORT`).
- **Zero-Dependency Startup**: Operates immediately out-of-the-box using the built-in synthetic in-memory SQLite warehouse. No external database provisioning is required for instant portfolio demonstrations.
- **Automated Health Probes**: Pre-configured with Render's health check monitoring against `GET /health`.
- **Free Tier Compatible**: Runs within Render's free Web Service tier (512MB RAM).

---

## 🚀 Method A: 1-Click Blueprint Deployment (Recommended)

DataPilot includes a native [`render.yaml`](../render.yaml) blueprint specification.

1. **Push your repository** to your personal GitHub / GitLab account:
   ```bash
   git init
   git add .
   git commit -m "feat: complete DataPilot autonomous database analyst"
   git remote add origin https://github.com/<your-username>/datapilot.git
   git push -u origin main
   ```
2. Log in to [Render Dashboard](https://dashboard.render.com).
3. Click **New +** in the top navigation bar, then select **Blueprint**.
4. Connect your `datapilot` repository.
5. Render will automatically detect [`render.yaml`](../render.yaml) and parse:
   - **Service Name**: `datapilot`
   - **Runtime**: `Docker`
   - **Health Check Path**: `/health`
   - **Plan**: `Free`
6. Render will prompt you for `LLM_API_KEY`:
   - Enter your SiliconFlow / OpenAI / Gemini API key.
7. Click **Apply**.
8. Render will build the multi-stage Docker image and deploy your live URL (e.g. `https://datapilot.onrender.com`).

---

## 🛠️ Method B: Manual Web Service Deployment (Docker)

If you prefer setting up the web service manually without blueprints:

1. In the **Render Dashboard**, click **New +** → **Web Service**.
2. Select **Build and deploy from a Git repository** and pick your `datapilot` repository.
3. Configure the following service settings:

| Setting | Value | Notes |
| :--- | :--- | :--- |
| **Name** | `datapilot` | Or your preferred subdomain |
| **Region** | `Oregon (US West)` or closest | Free tier available |
| **Branch** | `main` | Production branch |
| **Runtime** | **Docker** | Uses root `Dockerfile` |
| **Dockerfile Path** | `./Dockerfile` | Multi-stage builder |
| **Docker Context** | `.` | Root context |
| **Instance Type** | **Free** (0.1 CPU, 512 MB RAM) | Fully sufficient for DataPilot |

4. Under **Advanced Settings**, configure:
   - **Health Check Path**: `/health`
   - **Auto-Deploy**: `Yes`

5. Under **Environment Variables**, add:

| Key | Value | Description |
| :--- | :--- | :--- |
| `LLM_API_KEY` | `gsk_...` | Your Groq API key |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | Ultra-fast Groq Llama 3.3 model |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Groq OpenAI-compatible endpoint |
| `ENABLE_EXTERNAL_SERVICES` | `false` | Enables standalone synthetic dev DB |

6. Click **Create Web Service**.

---

## 🐍 Method C: Native Python Deployment (Without Docker)

If you prefer building without Docker using Render's native Python runtime:

1. In **Render Dashboard**, click **New +** → **Web Service**.
2. Select **Runtime**: **Python 3**.
3. Set the following build and start commands:
   - **Build Command**:
     ```bash
     cd frontend && npm install && npm run build && cd .. && pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn main:app --host 0.0.0.0 --port $PORT
     ```
4. Set **Health Check Path**: `/health`.
5. Add the environment variables listed in Method B.
6. Click **Create Web Service**.

---

## 🔍 Post-Deployment Verification

Once Render finishes deploying (indicated by a green `Live` status):

1. **Open the Web UI**:
   Navigate to `https://<your-service-name>.onrender.com`. You should see the DataPilot Analyst dashboard.
2. **Verify the Healthcheck Probe**:
   Visit `https://<your-service-name>.onrender.com/health`.
   ```json
   {
     "status": "healthy",
     "service": "datapilot",
     "version": "1.0.0",
     "mode": "standalone_synthetic"
   }
   ```
3. **Verify Interactive API Documentation**:
   Visit `https://<your-service-name>.onrender.com/docs`.
4. **Run Live Natural Language Query**:
   In the chat box on the web interface, ask:
   > *"Show me the top five products with the highest sales this month"*
   The system will dynamically retrieve schemas, generate candidates with blind subagents, pass AST safety validation, query the database, and return the structured report and interactive data table.
5. **Run the Benchmark Endpoint**:
   Visit `https://<your-service-name>.onrender.com/api/datapilot/benchmark`.
   Verifies 100% accuracy on all 14 test scenarios directly in production.

---

## 💡 Render Troubleshooting & Tips

- **Free Tier Spin-Down**: Render's free tier puts inactive services to sleep after 15 minutes. The initial request might take 30–50 seconds to wake up the container.
- **Port Binding**: Do not hardcode port `8000` in custom commands; Render automatically injects the `$PORT` environment variable (typically `10000`). DataPilot's `Dockerfile` and `main.py` dynamically bind to `${PORT:-8000}`.
- **Viewing Logs**: Go to **Logs** in your Render service dashboard to view real-time request tracing with unique `X-Request-ID` headers.

