from fastapi import FastAPI

from app.content.router import router as content_router


app = FastAPI(
    title="Newsletter Reference Architecture API",
    version="0.1.0",
)


app.include_router(content_router)


@app.get("/")
def root():
    return {"message": "Newsletter Reference Architecture API"}