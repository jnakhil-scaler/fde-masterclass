from fastapi import FastAPI

app = FastAPI(title="Gupta Building Materials API")


@app.get("/health")
def health():
    return {"status": "ok"}
