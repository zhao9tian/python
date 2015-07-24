mport requests
import paramiko
import os
import time

__author__ = 'xiaoyao'

LOGIN_URL = 'http://admin.tesla.mogujie.org/login'
USER_NAME = 'xiaoyao'
PASSWORD = 'xxxxxxx'
SSH_USER = 'xiaoyao'
SSH_PASSWD = 'xxxxx'
TESLA_DEPLOY_PATH = '/usr/local/tesla/'
LOCAL_FILE = '/Users/xiaoyao/Workspace/java/item-center/target/item-center.tar.gz'
REMOTE_FILE = '/tmp/item-center.tar.gz'
SERVER_LIST = ['10.15.6.11', '10.11.7.55', '10.11.7.58', '10.11.2.203', '10.11.2.204']
OFFLINE_URL_TMPL = 'http://admin.tesla.mogujie.org/application/itemcenter/concrete/%s/disable'
ONLINE_URL_TMPL = 'http://admin.tesla.mogujie.org/application/itemcenter/concrete/%s/able'
LOG_BAK_PATH = "/usr/local/tesla/log_bak"
SERVICE_NAME = "item-center"



def on_or_offline_service(ip, doOnline = False):
    _s = requests.session()
    _login_data = {'username':USER_NAME, 'password':PASSWORD}
    _ret = _s.post(LOGIN_URL, _login_data)
    if _ret.status_code != 200:
        print "登陆失败"
        return False
    op_ret = _s.get(ONLINE_URL_TMPL % ip if doOnline else OFFLINE_URL_TMPL % ip)
    if 'ok' == op_ret.text:
        print "offline service successfully!"
        return True
    else :
        print "offline service failed!"
        return False

def upload_pkg(ip, port=10022):
    try:
        _ssh = paramiko.SSHClient()
        _ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
        _ssh.connect(ip, username=SSH_USER, password=SSH_PASSWD, port=port)
        _sftp = _ssh.open_sftp()
        _sftp.put(LOCAL_FILE, REMOTE_FILE)
        _sftp.close()
        _ssh.close()
    except Exception, e:
        print e
        print "upload failed!"
        return False
    print "upload successfully!"
    return True

def check_live(ip, port=10022):
    _ssh = paramiko.SSHClient()
    _ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
    _ssh.connect(ip, username=SSH_USER, password=SSH_PASSWD, port=port)
    _counter = 0
    _last_ret = ''
    _is_live = False
    while True:
        _stdin, _stdout, _stderr = _ssh.exec_command('ls -l /usr/local/tesla/item-center/logs/item-center-request.log',  timeout = 20.0)
        _ret = _stdout.readlines()
        if _last_ret == _ret:
            _counter += 1
        else:
            _counter -= 1
        _last_ret = _ret
        if _counter > 5:
            print "die....."
            _is_live = False
            break
        elif _counter < -5:
            print "live....."
            _is_live = True
            break
        time.sleep(1)
    _ssh.close()
    return _is_live



def backup(ip, port=10022):
    _ret = False
    _ssh = paramiko.SSHClient()
    try:
        _ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
        _ssh.connect(ip, username=SSH_USER, password=SSH_PASSWD, port=port)
        _ssh.exec_command("mkdir /usr/local/tesla/log_bak/")
        _stdin, _stdout, _stderr = _ssh.exec_command("tar zcvf /usr/local/tesla/bak/" + SERVICE_NAME + str(time.time()) +".tar.gz /usr/local/tesla/"+SERVICE_NAME+"/**",  timeout = 20.0)
        if len(_stderr.readlines()) < 3:
            print "back up successfully!"
            _ret = True
        else:
            print "back up failed!"
            _ret = False
    except Exception, e:
        print e
        print "back up failed!"
    _ssh.close()
    return _ret


def start_or_stop_service(ip, doStart = False, port=10022):
    _ret = False
    _ssh = paramiko.SSHClient()
    _op = "start" if doStart else "stop"
    try:
        _ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
        _ssh.connect(ip, username=SSH_USER, password=SSH_PASSWD, port=port)
        _, _out, _ = _ssh.exec_command("/usr/local/tesla/item-center/bin/" + _op + ".sh",  timeout = 20.0)
        time.sleep(20)
        _stdin, _stdout, _stderr = _ssh.exec_command("ps aux | grep item-center | grep -v grep | grep -v start.sh | grep -v stop.sh")
        _grep_ret = _stdout.readlines()
        print str(len(_grep_ret))
        if (not doStart and len(_grep_ret) == 0) or (doStart and len(_grep_ret) == 1):
            print _op + " successfully!"
            _ret = True
        else:
            print _op + " failed!"
            _ret = False
    except Exception, e:
        print e
        print _op + " failed!"
    _ssh.close()
    return _ret

def refresh_files(ip, port=10022):
    _ret = False
    _ssh = paramiko.SSHClient()
    try:
        _ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
        _ssh.connect(ip, username=SSH_USER, password=SSH_PASSWD, port=port)
        _, _stdout, _stderr_rm = _ssh.exec_command("rm -rf /usr/local/tesla/"+SERVICE_NAME + "**",  timeout = 100.0)
        _stdout.read()
        _, _stdout, _stderr_unzip = _ssh.exec_command("tar zxvf /tmp/" + SERVICE_NAME + ".tar.gz -C /usr/local/tesla/",  timeout = 100.0)
        _stdout.read()
        _, _stdout, _stderr_chmod = _ssh.exec_command("chmod -R 777 /usr/local/tesla/"+SERVICE_NAME,  timeout = 100.0)
        _stdout.read()
        if len(_stderr_rm.readlines()) == 0 or len(_stderr_unzip.readlines()) == 0 or len(_stderr_chmod.readlines()) == 0:
            print "refresh files successfully!"
            _ret = True
        else:
            print "refresh files failed!"
            _ret = False
    except Exception, e:
        print e
        print "refresh failed!"
    _ssh.close()
    return _ret



def deploy(ip) :
    print "start deploy " + ip
    if on_or_offline_service(ip) and upload_pkg(ip) and not check_live(ip) and backup(ip) and start_or_stop_service(ip,
                                                                                                                    False) and refresh_files(
            ip) and start_or_stop_service(ip, True) and on_or_offline_service(ip, True) and check_live(ip):
        print "success"
        print "*****************************************************"
        return True
    else:
        print "fail"
        print "*****************************************************"
        return False



if __name__ == "__main__":
    # for _server in SERVER_LIST:
    #     ret = deploy(_server)
    #     break
