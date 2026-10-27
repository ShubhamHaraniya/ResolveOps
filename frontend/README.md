# ResolveOps frontend

Next.js 16 / React 19 / Tailwind 4 / Recharts dashboard for the ResolveOps backend.

```bash
npm install
npm run dev        # http://localhost:3000
npm run lint
npm run build
```

The app proxies `/api/*` and `/ready` to the FastAPI backend. The target defaults to
`http://127.0.0.1:8000`; override it with the `BACKEND_URL` environment variable when
starting `next dev` / `next start` (or building).

Every page reads live data from the backend and shows an empty or error state when there is
none; there is no bundled sample data.
