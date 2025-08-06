import logging
from logging.handlers import RotatingFileHandler
import os
from app import create_app

# Configure logging
if not os.path.exists('logs'):
    os.mkdir('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        RotatingFileHandler('logs/app.txt', maxBytes=10240, backupCount=10),
        logging.StreamHandler()
    ]
)

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)