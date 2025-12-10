import paramiko
from datetime import datetime, timedelta

SSH_HOST = "192.99.110.188"
SSH_USER = "root"
SSH_PASS = "SUA_SENHA_AQUI"

def create_ssh_user(username, password, days):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS)

        # data de expiração
        expire_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        # comandos do SSH PLUS PRO
        commands = [
            f"useradd -M -s /bin/false {username}",
            f"echo '{password}\n{password}' | passwd {username}",
            f"chage -E {expire_date} {username}"
        ]

        output = ""
        for cmd in commands:
            stdin, stdout, stderr = client.exec_command(cmd)
            output += stdout.read().decode() + stderr.read().decode()

        client.close()
        return {"success": True, "log": output}

    except Exception as e:
        return {"success": False, "error": str(e)}

def delete_ssh_user(username):
    try:
        command = f"userdel -rf {username}"
        result = ssh.execute(command)
        return {"status": "deleted", "output": result}
    except Exception as e:
        return {"error": str(e)}

def renew_ssh_user(username, days):
    try:
        command = f"chage -E $(date -d '+{days} days' +%s) {username}"
        result = ssh.execute(command)
        return {"status": "renewed", "output": result}
    except Exception as e:
        return {"error": str(e)}
    
    
def delete_ssh_user(username):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("192.99.110.188", username="root", password="3zFS3LqZ30NeN")

        command = f"deluser {username}"
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        client.close()

        return output

    except Exception as e:
        return str(e)

