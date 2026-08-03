from fastapi import FastAPI

from app.routers import products, customers, suppliers, orders, credit

app = FastAPI(title="Gupta Building Materials API")

app.include_router(products.router)
app.include_router(customers.router)
app.include_router(suppliers.router)
app.include_router(orders.router)
app.include_router(credit.router)


@app.get("/health")
def health():
    return {"status": "ok"}
