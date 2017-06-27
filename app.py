from flask import Flask,render_template
from flask_bootstrap import Bootstrap
from flask_script import Manager
from flask_moment import Moment
from datetime import datetime
from client import SshClient
import sqlite3
from sshinfo import retrieve_servers, process_info, update_db, retrieve_server_history
from apscheduler.scheduler import Scheduler
import atexit
import logging
logging.basicConfig()


app = Flask(__name__)
app.debug = True
manager = Manager(app)
bootstrap = Bootstrap(app)
moment = Moment(app)
cron = Scheduler(daemon=True)

@cron.interval_schedule(seconds=20)
def job_function():
    update_db()

cron.start()


@app.route('/',  methods=['GET', 'POST'])
def index():
    server_list = retrieve_servers()
    return render_template('index.html',
        current_time=datetime.utcnow(),
        servers=server_list,
        info='')


@app.route('/<name>', methods=['GET', 'POST'])
def user(name):
    server_list = retrieve_servers()
    retrieve_server_history(name)
    for row in server_list:
        if row['id'] == str(name):
            gpus, processes = process_info(row['info'])
    return render_template('index.html',
        current_time=datetime.utcnow(),
        servers=server_list,
        gpus=gpus,
        processes=processes)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'),404


atexit.register(lambda: cron.shutdown(wait=False))
if __name__ == "__main__":
    manager.run()
