from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth

# Membuat semua tabel di database (kalau belum ada)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="drrew_template API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # persempit sesuai kebutuhan produksi nanti
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],    
)

app.include_router(auth.router)


@app.get("/")
def read_root():
    return {"message": "drrew_template API is running"}