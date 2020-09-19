import paramiko
import re
import os
import time
import logging
import configparser


host = "134.111.87.198"
user = "root"
pw = "syseng"
port = 22

logging.basicConfig(level=logging.INFO)
my_files = "my_files"
vib_script = "vib_copy.py"
aul_script = "AUL.py"
aul_upgrade1 = "AUL_Upgrade12.py"
esx_post_install = "esx_install.py"
esx_postinstall = "esx_postinstall.pl"

config = configparser.ConfigParser()
config.read('c:\\auto\\BasicConfig.txt')
section = config.sections()

input_dir = config[section[0]]['Project_dir']
input_subdir = config[section[0]]['Build_dir']
app = config[section[0]]['App_IP']
app_pwd = config[section[0]]['app_pwd']
host_esx = config[section[0]]['Host_esx_IP']
host_esx_pw = config[section[0]]['host_esx_pw']

transport_obj = paramiko.Transport((host, port))
transport_obj.connect(username=user, password=pw)
sftp_client = paramiko.SFTPClient.from_transport(transport_obj)


class AULException(Exception):
    pass


def upload_file(source, target):
    logging.info('Establish session with {} to upload file'.format(app))
    app_trans_obj = paramiko.Transport((app, port))
    app_trans_obj.connect(username=user, password=app_pwd)
    trans_client = paramiko.SFTPClient.from_transport(app_trans_obj)
    try:
        trans_client.put(source, target, callback=None)
        logging.info('Upload of {} to {} completed'.format(source, target))
    except Exception:
        error_msg = 'Failed to upload {}'.format(source)
        logging.error(error_msg)
        raise AULException(error_msg)


def download_file(source, destination):
    try:
        sftp_client.get(source, destination, callback=None)
        logging.info('Completed download of {}'.format(source))
    except Excpetion:
        error_msg = 'Failed to download {}'.format(source)
        logging.error(error_msg)
        raise AULException(error_msg)


def ssh_connection(host_ip, user_name, user_pass):
    ssh_obj = paramiko.SSHClient()
    ssh_obj.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_obj.connect(host_ip, username=user_name, password=user_pass)
    return ssh_obj


def run_ssh_cmd(ssh_obj, command):
    stdin, stdout, stderr = ssh_obj.exec_command(command)
    return stdout.read().decode('ascii').strip("\n")


def set_up():
    logging.info('Open ssh connection to {} with user {} and password {}'.format(app, user, app_pwd))
    ssh_obj = ssh_connection(app, user, app_pwd)
    # Assuming Ubuntu on the app server. Need to change the commands as per the OS
    logging.info('Update packages')
    cmd = 'sudo apt-get update -y'
    run_ssh_cmd(ssh_obj, cmd)
    logging.info('Install python setuptools')
    cmd = 'sudo apt-get install -y python3-setuptools'
    run_ssh_cmd(ssh_obj, cmd)
    logging.info('Install pip')
    cmd = 'sudo apt-get install -y python3-pip'
    run_ssh_cmd(ssh_obj, cmd)
    logging.info('Install pexpect')
    cmd = 'sudo pip3 install pexpect'
    run_ssh_cmd(ssh_obj, cmd)
    logging.info('Verify pexpect installation')
    cmd = 'pip show pexpect'
    pdata = run_ssh_cmd(ssh_obj, cmd)
    if "Version:" in str(pdata):
        logging.info("prerequisite are met now other things execute:")
    else:
        error_msg = 'Prerequisite are not met please check'
        logging.error(error_msg)
        raise AULException(error_msg)


def get_file_vib(files_list):
    vib, ret_file = None, None
    for file_name in files_list:
        match_obj = re.search(r'.*.vib', file_name)
        if match_obj:
            vib = match_obj.group()

        match_obj = re.search(r'ftSys_for_ESX.*iso', file_name)
        if match_obj:
            ret_file = file_name

    if vib and ret_file:
        return vib, ret_file
    else:
        raise AULException('Failed to get vib file and its iso file names')


def verify_pivot():
    verify_flag = False
    # TODO: Assuming timeout is 45 mins. Fix this
    timeout = time.time() + 60 * 45
    command = 'ping -n 1 {}'.format(app)
    while time.time() < timeout:
        data = os.system(command)
        output = str(data).split(" ")
        logging.info(output)
        if not int(output[0]):
            logging.info("System UP")
            verify_flag = True
            break
        time.sleep(120)
        logging.info("System is Pivoting ... not UP will ping after 5 min")
    if not verify_flag:
        raise AULException('Timeout: Failure to reboot. System {} is down'.format(app))


def set_sync_speed(min_value=500000, max_value=500000):
    ssh_obj = ssh_connection(host_esx, user, host_esx_pw)

    logging.info('Set syncing speed of esx')
    cmd = 'esxcli storage mpm speedLimit --min={} --max={}'.format(min_value, max_value)
    run_ssh_cmd(ssh_obj, cmd)
    logging.info('ESX sync speed set min: {} and max: {}'.format(min_value, max_value))

    cmd = 'esxcli storage mpm speedLimit'
    run_ssh_cmd(ssh_obj, cmd)


def check_sync_status():
    sync_flag = False
    ssh_obj = ssh_connection(host_esx, user, host_esx_pw)
    cmd = 'esxcli storage mpm list'

    # TODO: Assuming timeout is 45 mins. Fix this
    timeout = time.time() + 60 * 45
    while time.time() < timeout:
        output = run_ssh_cmd(ssh_obj, cmd)
        if 'resync=' in output:
            logging.info("Disks sync is in-progress")
            time.sleep(300)
        elif 'in_sync' in output:
            logging.info("Completed disks sync")
            sync_flag = True
            break
        else:
            logging.error('Weired sync output: {}'.format(output))
            break
    if not sync_flag:
        raise AULException('Disks sync failed')


def duplex_state():
    ssh_obj = ssh_connection(app, user, app_pwd)

    logging.info("running ft-verify command. please wait for output")
    cmd = '/opt/ft/sbin/ft-verify -D'
    output = run_ssh_cmd(ssh_obj, cmd)
    # TODO: Sleep might not be required
    time.sleep(120)
    logging.info(output)

    app_version1, dup_state1 = None, None

    app_version = re.search(r"\(.*\)", str(output))
    if app_version:
        app_version1 = app_version.group()
        logging.info("Appliance version installed: {}".format(app_version1))
    else:
        raise AULException('Failed to get appliance version')

    dup_state = re.search(r"ftServer CRUs duplexed(\s+)(\[\w+\])", str(output))
    if dup_state:
        if '[PASS]' in dup_state.group(2):
            dup_state1 = "Systems are duplexed"
        else:
            AULException('Systems are not duplexed. May be some issues')
    else:
        AULException('Failed to get system duplex state')

    return app_version1, dup_state1
    

def aul_install():
    common_path = '/test1/Aeries_New/ftESX'

    set_up()

    source_file = '{}/{}/{}'.format(common_path, input_dir, input_subdir)
    files = sftp_client.listdir(source_file)
    vib, file = get_file_vib(files)

    source_file = '{}/{}/{}/{}'.format(common_path, input_dir, input_subdir, file)
    dest_file = r'C:\auto\{}'.format(file)
    logging.info("Downloading the iso file")
    download_file(source_file, dest_file)

    upload_location = "/root/{}".format(file)
    logging.info("Uploading the iso file")
    upload_file(dest_file, upload_location)

    aul_file = r'C:\auto\{}'.format(aul_script)
    upload_location = '/root/{}'.format(aul_script)
    logging.info('Uploading the Appliance Script')
    upload_file(aul_file, upload_location)

    logging.info("SSH to Appliance")
    ssh_obj = ssh_connection(app, user, app_pwd)

    logging.info("Executing AUL script")
    cmd = "python /root/{} {} {} {}".format(aul_script, file, host_esx, host_esx_pw)
    logging.info("Installing AUL Please wait.........")
    output = run_ssh_cmd(ssh_obj, cmd)
    logging.info(output)

    time.sleep(10)

    match_obj = re.search(r'reboot', str(output))
    if match_obj.group() == "reboot":
        logging.info('AUL installed rebooting the appliance...')
        ssh_obj = sh_connection(host_esx, user, host_esx_pw)
        run_ssh_cmd(ssh_obj, 'reboot')
    else:
        raise AULException('AUL not properly installed so exiting')

    verify_pivot()
    set_sync_speed()
    check_sync_status()
    duplex_state()


def vib_uninstall():

    ssh_obj = ssh_connection(host_esx, user, host_esx_pw)

    logging.info("Uninstalling vib tool in esx host")
    cmd = 'esxcli software vib remove --vibname qatools'
    uninstall_vib = run_ssh_cmd(ssh_obj, cmd)
    logging.info(uninstall_vib)

    check_message = re.search(r"vib uninstalled successfully reboot system", str(uninstall_vib))
    if check_message:
        logging.info("vib uninstalled successfully reboot system")
        run_ssh_cmd(ssh_obj, 'reboot')
    else:
        raise AULException('vib not installed successfully')

    # TODO: Sleep might be avoided
    time.sleep(600)


def check_vib_uninstall():
    ssh_obj = ssh_connection(host_esx, user, host_esx_pw)
    cmd = 'esxcli software vib list | grep qatools'
    vib_status = run_ssh_cmd(ssh_obj, cmd)

    match_obj = re.search(r"qatools", str(vib_status))
    if not match_obj:
        logging.info('vib not installed in the system')
        return True
    else:
        logging.info('vib installed in the system')
        return False


def vib_install():
    common_path = '/test1/Aeries_New/ftESX'

    set_up()

    logging.info("Installing vib tool in esx host")
    source_file = "{}/{}/{}".format(common_path, input_dir, input_subdir)
    files = sftp_client.listdir(source_file)
    vib, file = get_file_vib(files)

    destination_file = r'C:\auto\{}'.format(vib)
    logging.info('Downloading the vib file')
    source_file = "{}}/{}/{}/{}".format(common_path, input_dir, input_subdir, vib)
    download_file(source_file, destination_file)

    file_s = r'C:\auto\{}'.format(vib_script)
    upload_location = "/root/{}".format(vib_script)
    upload_file(file_s, upload_location)

    file_vib1 = '{}/{}/{}/{}'.format(common_path, input_dir, input_subdir, vib)
    destination_file = r'C:\auto\{}'.format(vib)
    download_file(file_vib1, destination_file)

    logging.info('Uploading file {}'.format(vib))
    file_vib = r'C:\auto\{}'.format(vib)
    logging.info(file_vib)
    upload_location = '/root/{}'.format(vib)
    upload_file(file_vib, upload_location)

    ssh_obj = ssh_connection(app, user, app_pwd)
    logging.info('Copying vib to esx host')
    cmd = 'python /root/vib_copy.py {} {} {}'.format(vib, host_esx, host_esx_pw)
    logging.info(cmd)
    output = run_ssh_cmd(ssh_obj, cmd)
    logging.info(output)

    ssh_obj = ssh_connection(host_esx, user, host_esx_pw)
    cmd = 'esxcli software vib install -v /tmp/{} --force'.format(vib)
    install_vib = run_ssh_cmd(ssh_obj, cmd)
    logging.info(install_vib)

    check_install = re.search(r'The update completed successfully', str(install_vib))
    if check_install:
        logging.info('vib installed successfully reboot system')
        run_ssh_cmd(ssh_obj, 'reboot')
    else:
        raise AULException('vib not  installed successfully')

    # TODO: Sleep might be handled in another way
    time.sleep(600)

    ssh_obj = ssh_connection(host_esx, user, host_esx_pw)
    cmd = 'esxcli software vib list | grep qatool'
    output = run_ssh_cmd(ssh_obj, cmd)
    match_obj = re.search(r"\d.\d.\d-\d+", str(output))
    # TODO: Proper check on match object is required
    logging.info('vib version installed :{}'.format(match_obj.group()))


def aul_upgrade():
    logging.info('Checking Whether VIB installed in the system.....')
    vib_status = check_vib_uninstall()
    if vib_status:
        logging.info('VIB not installed in the system so proceeding with AUL upgrade')
    else:
        logging.info('VIB is installed in the system so proceeding with VIB uninstall')
        vib_uninstall()

    logging.info('Checking system health please wait.....')
    appliance_ver, dup_state = duplex_state()
    logging.info('Current installed appliance version is {}'.format(appliance_ver))
    logging.info('System is healthy & {}'.format(dup_state))

    common_path = '/test1/Aeries_New/ftESX'

    source_file = '{}/{}/{}'.format(common_path, input_dir, input_subdir)
    files = sftp_client.listdir(source_file)
    vib, file = get_file_vib(files)

    source_file = '{}/{}/{}/{}'.format(common_path, input_dir, input_subdir, file)
    destination_file = r'C:\auto\{}'.format(file)
    logging.info("Downloading the iso file")
    download_file(source_file, destination_file)

    upload_location = '/root/{}'.format(file)
    logging.info('Uploading the iso file')
    upload_file(destination_file, upload_location)

    aul_file = r'C:\auto\{}'.format(aul_upgrade1)
    upload_location = '/root/{}'.format(aul_upgrade1)
    logging.info('Uploading the Appliance Script')
    upload_file(aul_file, upload_location)

    ssh_obj = ssh_connection(app, user, app_pwd)

    logging.info('Executing upgrade AUL script')
    cmd = 'python /root/{} {} {} {}'.format(aul_upgrade1, file, host_esx, host_esx_pw)
    logging.info("Upgrading AUL Please wait.... ....")
    output = run_ssh_cmd(ssh_obj, cmd)
    logging.info(output)

    match_obj = re.search(r'reboot', str(output))
    if match_obj.group() == 'reboot':
        logging.info('AUL upgraded rebooting the appliance')
        # TODO: check correctness of the SSH connection
        ssh_obj = ssh_connection(host_esx, user, host_esx_pw)
        run_ssh_cmd(ssh_obj, 'reboot')
    else:
        raise AULException('AUL not properly installed so exiting')

    verify_pivot()
    # set_sync_speed()
    check_sync_status()
    current_appliance_ver, dup_state = duplex_state()
    logging.info('AUL is upgraded from {} to {} successfully'.format(appliance_ver, current_appliance_ver))


def cleanup():
    common_path = '/test1/Aeries_New/ftESX'

    logging.info('Cleaning files in appliance')
    source_file = '{}/{}/{}'.format(common_path, input_dir, input_subdir)
    files = sftp_client.listdir(source_file)
    vib, file = get_file_vib(files)

    ssh_obj = ssh_connection(app, user, app_pwd)

    cmd = 'rm -rf AUL.pl vib_copy.py {} {} {}'.format(file, my_files, vib)
    run_ssh_cmd(ssh_obj, cmd)

    logging.info('Removing files')
    ls_files = os.listdir()
    files_remove = [i for i in ls_files if i.endswith('iso') or i.endswith('vib')]
    for file_name in files_remove:
        os.remove(file_name)


if __name__ == "__main__":
    # TODO: call the methods
    cleanup()
