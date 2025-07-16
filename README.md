# webhook-repo
Dev Assessment - Webhook Receiver
Please use this repository for constructing the Flask webhook receiver.

Setup
Create a new virtual environment
pip install virtualenv
Create the virtual env
virtualenv venv
Activate the virtual env
source venv/bin/activate
Install requirements
pip install -r requirements.txt
Run the flask application (In production, please use Gunicorn)
python run.py
The endpoint is at:
POST http://127.0.0.1:5000/webhook/receiver
You need to use this as the base and setup the flask app. Integrate this with MongoDB (commented at app/extensions.py)
