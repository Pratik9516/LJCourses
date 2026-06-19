from app import create_app
from app.db import engine, Base
import app.models

# Automatically tables banata hai Render pe
with engine.connect():
    Base.metadata.create_all(bind=engine)

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5001, host='127.0.0.1')
