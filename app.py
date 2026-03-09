from api.app import app
import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        reload=True,
        forwarded_allow_ips="*",
        log_config="utils/logger/config.json",
    )
