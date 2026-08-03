from fastapi import FastAPI

from app.routers import products, customers, suppliers

app = FastAPI(title="Gupta Building Materials API")

app.include_router(products.router)
app.include_router(customers.router)
app.include_router(suppliers.router)


@app.get("/health")
def health():
    return {"status": "ok"}
