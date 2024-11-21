import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from oufoaler.config import config
from oufoaler.controllers.car_controller import CarController
from oufoaler.views.api import router as api_router

logging.basicConfig(level=getattr(logging, config.logging_level.upper()))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()

# Include sub-routers
app.include_router(api_router)
#
# Add static files and templates
app.mount("/static", StaticFiles(directory="oufoaler/views/static"), name="static")
templates = Jinja2Templates(directory="oufoaler/views/templates")
#
# Load controllers
car_ctrl = CarController()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    cars = [car.__dict__ for car in car_ctrl.get_cars()]
    return templates.TemplateResponse(
        request=request, name="index.html", context={"cars": cars}
    )


# Health Endpoint
@app.get("/health", response_class=JSONResponse)
async def health():
    return {"status": "ok", "msg": "healthy"}


def run():
    uvicorn.run("oufoaler.app:app", host=config.host, port=config.port, reload=False)


if __name__ == "__main__":
    run()
