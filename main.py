from fastapi import FastAPI
from app.database import engine, Base
from app.routers import auth

# Membuat semua tabel di database (kalau belum ada)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="drrew_template API", version="1.0.0")

app.include_router(auth.router)


@app.get("/")
def read_root():
    return {"message": "drrew_template API is running"}