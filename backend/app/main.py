from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import products, customers, suppliers, orders, credit, agents

app = FastAPI(title="Gupta Building Materials API")

app.include_router(products.router)
app.include_router(customers.router)
app.include_router(suppliers.router)
app.include_router(orders.router)
app.include_router(credit.router)
app.include_router(agents.router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve the built React frontend. Mounted last so it acts as a catch-all
# without shadowing any API routes registered above.
FRONTEND_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
