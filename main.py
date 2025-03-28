import uvicorn
from src.server import create_app
from src.config import Config

if __name__ == '__main__':
    app = create_app()
    uvicorn.run(app, host=Config.HOST, port=Config.PORT) 