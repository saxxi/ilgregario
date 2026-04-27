from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from routers import auth, dashboard, admin

app = FastAPI(title="IlGregario")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return RedirectResponse("/login", status_code=302)
