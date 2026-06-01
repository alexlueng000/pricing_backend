from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings


app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError) -> JSONResponse:
    for error in exc.errors():
        field = error.get("loc", [""])[-1]
        if field == "display_order":
            return JSONResponse(status_code=422, content={"detail": "显示顺序必须为数字"})
        if field == "is_enabled":
            return JSONResponse(status_code=422, content={"detail": "状态不能为空"})
    return JSONResponse(status_code=422, content={"detail": "字段校验失败"})


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
