import os
from scanweave import create_app
from scanweave.scanner import install
from waitress import serve
app=create_app(os.environ.get('SCANWEAVE_DATA_DIR','data'))
install(app)
if __name__=='__main__':
    serve(app,host=os.environ.get('HOST','127.0.0.1'),port=int(os.environ.get('PORT','8912')),threads=6)
