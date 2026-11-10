# DataPilot Frontend Application

The conversational database analytics user interface for **DataPilot**, built with **React 19**, **Vite**, **Tailwind CSS**, and **Lucide Icons**.

## Getting Started

### 1. Install Dependencies
```bash
cd frontend
pnpm install
```

### 2. Run the Development Server
```bash
pnpm dev
```

By default, Vite proxies `/api` calls to `http://127.0.0.1:8000`, connecting to the FastAPI backend.

### 3. Custom Backend Target Configuration
To configure an alternative backend address:
```bash
cp .env.example .env
```
And adjust:
```bash
VITE_DEV_PROXY_TARGET=http://127.0.0.1:8000
```
For production deployments where the frontend and backend are hosted on separate domains, set:
```bash
VITE_API_BASE_URL=https://api.yourdomain.com
```

### 4. Build for Production
```bash
pnpm build
```
The compiled static assets will be output to `frontend/dist/`.
