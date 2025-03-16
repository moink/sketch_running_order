from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from handle_request import handle_running_order_request

app = FastAPI(title="Sketch Running Order API")

# Add CORS middleware if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock this down in production
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

@app.post("/optimize")
async def optimize_running_order(request: Request) -> JSONResponse:
    """Optimize the running order of sketches."""
    return JSONResponse(handle_running_order_request(request))
