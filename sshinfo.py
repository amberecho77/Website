#!/usr/bin/python

from StringIO import StringIO
import paramiko
import sqlite3
import datetime

class SshClient:
    "A wrapper of paramiko.SSHClient"
    TIMEOUT = 4

    def __init__(self, host, port, username, password, key=None, passphrase=None):
        self.username = username
        self.password = password
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if key is not None:
            key = paramiko.RSAKey.from_private_key(StringIO(key), password=passphrase)
        self.client.connect(host, port, username=username, password=password, pkey=key, timeout=self.TIMEOUT)

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None

    def execute(self, command, sudo=False):
        feed_password = False
        if sudo and self.username != "root":
            command = "sudo -S -p '' %s" % command
            feed_password = self.password is not None and len(self.password) > 0
        stdin, stdout, stderr = self.client.exec_command(command)
        if feed_password:
            stdin.write(self.password + "\n")
            stdin.flush()
        return {'out': stdout.readlines(),
                'err': stderr.readlines(),
                'retval': stdout.channel.recv_exit_status()}


def retrieve_info(ip, username, password):
    client = SshClient(host=ip, port=22, username=username, password=password)
    try:
       ret = client.execute('nvidia-smi', sudo=True)
    finally:
      client.close()
    return ret

IPs = ['10.80.43.134', '10.80.43.30', '10.80.43.95']
names = ['titan-pascal-4', 'dgx-8', 'm40-4']
admins = ['Zhou Bin', 'Zhou Bin', 'JK']
ids = range(len(IPs))
infos = []

def update_db():
    conn = sqlite3.connect('servers.db')
    c = conn.cursor()
    # c.execute('''CREATE TABLE servers
    #              (id text, IP text, names text, admins text, infos text, date text)''')
    infos = []
    dates = []
    now = datetime.datetime.now()
    for idx, ip in enumerate(IPs):
        ret = retrieve_info(ip, 'bzhou', '')
        info = "  ".join(ret["out"])
        infos.append(info)
        dates.append(now.strftime("%Y-%m-%d %H:%M:%S"))
    serverinfo = zip(ids, IPs, names, admins, infos, dates)
    c.executemany('INSERT INTO servers VALUES (?,?,?,?,?,?)', serverinfo)
    conn.commit()
    conn.close()

def retrieve_server_history(id):
    conn = sqlite3.connect('servers.db')
    c = conn.cursor()
    for row in c.execute('SELECT * FROM servers WHERE id = %s' % id):
        print row[1]


def retrieve_servers():
    conn = sqlite3.connect('servers.db')
    c = conn.cursor()
    server_list = []
    rows = []
    for row in c.execute('SELECT * FROM servers WHERE date IN (SELECT max(date) FROM servers)'):
        max_mem = 0
        mem_used = 0
        gpus, _ = process_info(row[4])

        for gpu in gpus:
            max_mem += int(gpu[5][:-3])
            mem_used += int(gpu[4][:-3])
        
        used_percent = int(mem_used / (max_mem + 0.001) * 100)

        iserver = {
            "IP": row[1],
            "date": row[5],
            "id": row[0],
            "name": row[2],
            "admin": row[3],
            "info": row[4],
            "usage": used_percent,
        }
        server_list.append(iserver)
    conn.close()
    return server_list[:3]

def process_info(info):
    info = info.split('\n')
    gpus = []
    processes = []

    for item in info:
        if 'MiB' in item and '%' in item:
            data = item.split('|')
            xx = data[1].strip().split(' ')
            xx = [x for x in xx if x != '']
            fans = xx[0]
            temp = xx[1]
            power = xx[3]
            power_max = xx[5]

            xx = data[2].strip().split(' ')
            xx = [x for x in xx if x != '']
            mem = xx[0]
            mem_max = xx[2]

            xx = data[3].strip().split(' ')
            xx = [x for x in xx if x != '']
            vol = xx[0]
            item_ = (fans, temp, power, power_max, mem, mem_max, vol)
            gpus.append(item_)
        if 'MiB' in item and '%' not in item:
            xx = item.split(' ')
            xx = [x for x in xx if x != '' and x != '|']
            gpuid = xx[0]
            pid = xx[1]
            name = xx[3]
            mem = xx[4]
            item_ = (gpuid, pid, name, mem)
            processes.append(item_)
    
    return gpus, processes
