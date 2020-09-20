##C:\Users\bnunna\Desktop\Ft_QA_Automation\ftESXAutomation\AUL_Install_upgrade_1.py
import paramiko
import re
import os
import time
import logging
import configparser
import random
import math
import argparse
import posixpath

from src.linux_utils.remote_system import RemoteSystem
from src.linux_utils.switch_utils import SwitchUtils
from src.linux_utils.vm_utils import VMUtils
from src.linux_utils.appliance_utils import ApplianceUtils
from src.logger_utils.logger import get_logger
from src.linux_utils.share_utils import ShareUtils
logger = get_logger(__name__)
vswitchname = 'cust_vSwitch1'
portgroupname = 'CustVM_PGrp'
uplinks = ['vmnic_100601', 'vmnic_110601']
# connect to host and grep available volume names, volume list needed for copying different vms on all volume
# provide static details of system and directory details

user = "root"
pw = "syseng"
esx_6 = "/VMstorage/ESX-VMTemplates/ESX6"
ESX_65 = "/VMstorage/ESX-VMTemplates/ESX7"
ESX_65 = "/ESX-VMTemplates/ESX7"

host_IP = "192.168.61.231"
#host_IP = "192.168.58.41"
appliance_ip = "192.168.61.230"
#appliance_ip = "192.168.58.42"
appliance_id = "root"
host_password = "syseng01!"
host_password = r'syseng01!'
appliance_pwd = "syseng"



share_username = "syseng"
share_pwd = "syseng"
share_ip = "134.111.87.198"
host_prompt = r"\[root@.*?]"
host_id = "root"
upload_AUL_loation=r'/root'
# number of vms required

existing_ds = list()
vm_loginid = 'root'
vm_loginpassword = 'syseng'
default_stressfile = '/input_decks/stressdeck.in'
stress_status_file = '/std_tools/MonitorTests'

MOUNT_IP = '134.111.87.198:/VMstorage'
Applnce_MOUNT_DIR = '/root/vmx_template_files'

host_id = "root"
DestComDirPath = "/vmfs/volumes"
port = 22

logging.basicConfig(level=logging.INFO)
my_files = "my_files"
vib_script="vib_copy.py"
aul_script="AUL.py"
AUL_Upgrade1="AUL_Upgrade12.py"
esx_post_install="esx_install.py"
esx_postinstall="esx_postinstall.pl"

def uplaod_file(file,dest_file):
    transport = paramiko.Transport((app, port))
    #logging.info (app,app_pwd)
    transport.connect(username = user, password = app_pwd)
    sftp = paramiko.SFTPClient.from_transport(transport)
    try:
        sftp.put(file,dest_file,callback=None)
        logging.info ("upload is completed")
    except:
        logging.info ("uplaod is Failed")
        exit


def download_file(file,dest_file):
    try:
        sftp.get(file,dest_file,callback=None)
        logging.info ("download is completed")
    except:
        logging.info ("download is Failed")
        exit()


def ssh_connection(host,user,pw,command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=user, password=pw)
    stdin, stdout, stderr = ssh.exec_command(command)
    #return str(stdout.readlines()).strip("\n")
    return stdout.read().decode('ascii').strip("\n")
    #return str(stdout.readlines()).decode('ascii').strip("\n")


def set_up():
	dest_file = "C:\\auto\\{}".format(my_files)
    
	#logging.info ("uploading the setup tools  {}".format(my_files))
	upload_loation="/root/{}".format(my_files)
	logging.info (uplaod_file(dest_file,upload_loation))

	logging.info ("untar the my_files ")
	command ="tar -xvf {}".format(my_files)
	logging.info (ssh_connection(app,user,app_pwd,command))
	logging.info ("installing the setup tools ")
	time.sleep(5)
	command="python /root/setuptools-41.0.1/setup.py install"
	logging.info (command)
	logging.info (ssh_connection(app,user,app_pwd,command))
	logging.info ("untar the PIP ")
	time.sleep(20)
	command ="tar -xvf pip-19.1.1.tar.gz"
	logging.info (ssh_connection(app,user,app_pwd,command))
	logging.info ("installing the  PIP ")
	command="cd /root/pip-19.1.1/; python setup.py install"
	logging.info (ssh_connection(app,user,app_pwd,command))
	time.sleep(10)
	logging.info ("installing pexpect")
	command="pip install pexpect"
	logging.info (command)
	logging.info (ssh_connection(app,user,app_pwd,command))
	time.sleep(10)
	command = "pip show  pexpect"
	pdata=ssh_connection(app,user,app_pwd,command)
	if "Version:" in str(pdata):
            logging.info ("prerequisite are met now other things execute:")
	else:
            logging.info ("prerequisite are not met please check")
            exit()

def remove_tar():
	command="rm -rf my_files pip-19.1.1.tar.gz pip-19.1.1 setuptools-41.0.1 "
	logging.info (ssh_connection(app,user,app_pwd,command))



def get_file_vib(files):
	for file1 in files:
            m=re.search(r".*.vib",file1)
            if m:
                vib=m.group()
            m=re.search(r"ftSys_for_ESX.*iso",file1)
    	
            if m:
                file=file1
	return vib,file





def verify_piviot():
    time.sleep(300)
    command="ping -n 1 {}".format((app))
    while True:
        data = os.system(command)
        d=str(data).split(" ")
        logging.info (d)
        if not int(d[0]):
            logging.info ("System UP")
            break
        time.sleep(200)
        logging.info ("System is Pivoting ... not UP will ping after 5 min")

def check_sync_status():
    while True:
        command="esxcli storage mpm list"
        data=ssh_connection(host_esx,user,host_esx_pw,command)
        sync=re.search(r"\w+=\d+\.\d+",str(data))
        finish=re.search(r"\w+=\d+\.\dmin",str(data))
        m =re.findall(r"\[\s\w+_?\w+\s\]",str(data))
        if not  "[ syncing ]" in m:
            logging.info ("all disk are synced")
            break
        time.sleep(300)
        logging.info ("Disk are  {0} & {1} please wait after few min will check again".format(sync.group(),finish.group()))
    time.sleep(120)
    logging.info ("Disk are synced now going to appliacne to check duplex state")


def duplex_state():
    logging.info ("running ft-verify coomad pleas wait for output")
    data=ssh_connection(app,user,app_pwd,"/opt/ft/sbin/ft-verify -D")
    time.sleep(60)
    logging.info (data)
    time.sleep(60)
    app_version=re.search(r"\(.*\)",str(data))
    logging.info ("Appliance versiom installed {}".format(app_version.group()))
    app_version1=app_version.group()
    duplex_state=re.search(r"ftServer CRUs duplexed(\s+)(\[\w+\])",str(data))
    if '[PASS]' in duplex_state.group(2):
        duplex_state1="system are duplexed"
        
    else:
        logging.info ("system are not  duplexed some issues")
        exit
    #host_esx_pw 
    #return app_version1,duplex_state1
    
  
def AUL_install():
    #set_up()
    #remove_tar()
    #source_file = "/test1/Aeries_New/ftESX/{0}/{1}".format(input_dir,input_subdir)
    #files = sftp.listdir(source_file)
    #vib,file=get_file_vib(files)
    #source_file = "/test1/Aeries_New/ftESX/{0}/{1}/{2}".format(input_dir,input_subdir,file)
    #dest_file = "C:\\auto\\{}".format(file)
    logging.info ("downloading the iso file")
    SrcVmImagepath='/test1/Aeries/Aeries_New/ftESX/ftESX-6.7.3/185/ftSys_for_ESX_6.7.3_185'    
    VMtemplateName='.iso'    
    Copy_AULBuild=app_obj.copy_vm_image(share_obj,SrcVmImagepath,upload_AUL_loation,VMtemplateName)
    if Copy_AULBuild:
        logging.info ('AUL Iso {} has copied successfully on appliance'.format(SrcVmImagepath))
    else:
        logging.info('AUL build not copied')
        return
    AUL_file = r'C:\Users\bnunna\Desktop\Ft_QA_Automation\ftESXAutomation\\{}'.format(aul_script)
    logger.info(AUL_file)
    
    '''
    download_file(source_file,dest_file)
    upload_loation="/root/{}".format(file)
    logging.info ("uploading the iso file")
    uplaod_file(dest_file,upload_loation)
    AUL_file = "C:\\auto\\{}".format(aul_script)
    upload_loation="/root/{}".format(aul_script)
    logging.info ("uploading the Appliance Script")
    uplaod_file(AUL_file,upload_loation)
    logging.info ("Executing AUL script")
    command="python /root/{0} {1} {2} {3}".format(aul_script,file,host_esx,host_esx_pw)
    logging.info ("Installing AUL Please wait.... ....")
    data1=ssh_connection(app,user,app_pwd,command)
    logging.info (data1)
    time.sleep(10)
    m=re.search(r"reboot",str(data1))
    if m.group() == "reboot":
        logging.info ("AUL installed rebooting the applaince ")
        ssh_connection(host_esx,user,host_esx_pw,"reboot")
    else:
        logging.info ("AUL not properly installed so exiting ")
        exit()
    verify_piviot()
    set_sync_speed()
    check_sync_status()
    duplex_state()
    '''








def vib_install():
    set_up()
    logging.info ("installing vib tool in esx host")
    source_file = "/test1/Aeries_New/ftESX/{0}/{1}".format(input_dir,input_subdir)
    files = sftp.listdir(source_file)
    vib,file=get_file_vib(files)
    dest_file = "C:\\auto\\{}".format(vib)
    logging.info ("downloading the vib file")
    source_file = "/test1/Aeries_New/ftESX/{0}/{1}/{2}".format(input_dir,input_subdir,vib)
    download_file(source_file,dest_file)
    file_s = "C:\\auto\\{}".format(vib_script)
    upload_loation="/root/{}".format(vib_script)
    upload_vib=uplaod_file(file_s,upload_loation)
    file_vib1="/test1/Aeries_New/ftESX/{0}/{1}/{2}".format(input_dir,input_subdir,vib)
    dest_file= "C:\\auto\\{}".format(vib)
    download_vib=download_file(file_vib1,dest_file)
    logging.info (download_vib)
    logging.info ("uploading file {}".format(vib))
    file_vib = "C:\\auto\\{}".format(vib)
    logging.info (file_vib)
    upload_loation="/root/{}".format(vib)
    upload_vib=uplaod_file(file_vib,upload_loation)
    logging.info(upload_vib)
    logging.info ("Copying vib to esx host")
    command="python /root/vib_copy.py {0} {1} {2}".format(vib,host_esx,host_esx_pw)
    logging.info (command)
    data=ssh_connection(app,user,app_pwd,command)
    logging.info (data)
    command ="esxcli software vib install -v /tmp/{} --force".format(vib)
    install_vib = ssh_connection(host_esx,user,host_esx_pw,command)
    logging.info(install_vib)
    vib_install =re.search(r"The update completed successfully",str(install_vib))
    if vib_install:
        logging.info("vib installed susceesfully reboot system")
        ssh_connection(host_esx,user,host_esx_pw,"reboot")
    else:
        logging.info("vib not  installed susceesfully ")
        exit()
    time.sleep(600)
    command = " esxcli software vib list | grep qatool"
    data=ssh_connection(host_esx,user,host_esx_pw,command)
    m=re.search(r"\d.\d.\d-\d+",str(data))
    logging.info ("vib version installaed :{}".format(m.group()))



def AUL_upgrade():
    logging.info("Checking Whether VIB installed in the system ..... ")
    Check_vib = vm_obj.check_vib_uninstall()
    if Check_vib:
        logging.info("VIB not installed in the system so proceeding with AUL upgrade ")
    else:
        logging.info("VIB is installed in the system so proceeding with VIB uninstall ")
        vm_obj.vib_uninstall()
    logging.info("Checking system health please wait..... ")
    appliance_ver,duplex_state12=duplex_state()
    print (f"current installed applaince version is {appliance_ver}\n")
    print (f"system is healthy & {duplex_state12}\n")
    source_file = "/test1/Aeries_New/ftESX/{0}/{1}".format(input_dir,input_subdir)
    files = sftp.listdir(source_file)
    vib,file=get_file_vib(files)
    source_file = "/test1/Aeries_New/ftESX/{0}/{1}/{2}".format(input_dir,input_subdir,file)
    dest_file = "C:\\auto\\{}".format(file)
    logging.info ("downloading the iso file")
    download_file(source_file,dest_file)
    upload_loation="/root/{}".format(file)
    logging.info ("uploading the iso file")
    uplaod_file(dest_file,upload_loation)
    AUL_file = "C:\\auto\\{}".format(AUL_Upgrade1)
    upload_loation="/root/{}".format(AUL_Upgrade1)
    logging.info ("uploading the Appliance Script")
    uplaod_file(AUL_file,upload_loation)
    logging.info ("Executing upgrade AUL script")
    command="python /root/{0} {1} {2} {3}".format(AUL_Upgrade1,file,host_esx,host_esx_pw)
    time.sleep(60)
    logging.info ("Upgrading AUL Please wait.... ....")
    data1=ssh_connection(app,user,app_pwd,command)
    logging.info (data1)
    m=re.search(r"reboot",str(data1))
    if m.group() == "reboot":
        logging.info ("AUL upgraded rebooting the applaince ")
        ssh_connection(host_esx,user,host_esx_pw,"reboot")
    else:
        logging.info ("AUL not properly installed so exiting ")
        exit()
    verify_piviot()
    #set_sync_speed()
    check_sync_status()
    current_appliance_ver,duplex_state12=duplex_state()
    print (f"AUL is upgraded from {appliance_ver} to {current_appliance_ver}  successfully")
    



def cleanUP():
    print ("cleaning files in appliance ")
    source_file = "/test1/Aeries_New/ftESX/{0}/{1}".format(input_dir,input_subdir)
    files = sftp.listdir(source_file)
    vib,file=get_file_vib(files)
    command="rm -rf AUL.pl  vib_copy.py  {0} {1} {2} ".format(file,my_files,vib)
    print(ssh_connection(app,user,app_pwd,command))
    print ("removing files ")
    ls_files =os.listdir()
    files_reomove=[i for i in ls_files if i.endswith( "iso") or i.endswith("vib")]
    for f in files_reomove:
          os.remove(file)
       
'''
    author    :   'Bharathi Nunna'
    This procedure performs the below steps
        1.Connects to appliance 
        2.
        
        Basic error handling
'''

def run_vm_stress_test(custom_images, total_vms):
    logger.info("Connect to vmware host")
    host_system = RemoteSystem(host_IP, host_id, host_password)
    host_system.connect_host()

    vm_obj = VMUtils(host_system)

    logger.info('Connect to applicance')
    appliance_system = RemoteSystem(appliance_ip, appliance_id, appliance_pwd)
    appliance_system.connect_host()

    app_obj = ApplianceUtils(appliance_system)

    logger.info("Connect to share to retrive vm template files")
    share_system = RemoteSystem(share_ip, share_username, share_pwd)
    share_system.connect_host()

    share_obj = ShareUtils(share_system)
    
    logger.info("Get existing VM-data configuration")
    existing_ds_vms_map = vm_obj.get_existing_ds_vms_map()
    if existing_ds_vms_map is False:
        logger.error('Failed Get existing VM-data configuration')
        return
        
        
    #Get ESX VM template path based on vmware version
    logger.info('Get esx template path')
    esx_image_path = vm_obj.get_esx_temp_path()
    if esx_image_path is False:
        logger.error('Failed to get vmware version')
        return
    

    wipe_vms_status = vm_obj.wipe_vms()
    if wipe_vms_status is False:
        logger.error('Failed to wipe existing VMs')
        return

    erase_stale_vm_status = vm_obj.erase_stale_vm_files()
    if erase_stale_vm_status is False:
        logger.error('Failed to clean the stale VM files in datastores')
        return
      
    
    print('getting existing datastores')
    existing_ds = vm_obj.get_existing_datastores()
    print('existing Data store are {}'.format(existing_ds))
    
    logger.info('creating new datastores if possible')
    app_obj.create_new_ds()
    print('getting existing datastores')
    existing_ds = vm_obj.get_existing_datastores()
    print('existing Data store are {}'.format(existing_ds))

    print('getting data datastores')
    data_datastores = [x for x in existing_ds if 'datastore' not in x]    
    print('actual data datastores are {}'.format(data_datastores))
    if len(data_datastores) == 0:
        print('Not enough datastores to create Vms')
        return
    
    usable_datastores = vm_obj.get_data_datastores()
    if len(usable_datastores) == 0:
        logger.error('No sufficient data datastores')

    logger.info('getting pre-configured vms')
    pre_configured_vms = vm_obj.get_existing_vms()

    logger.info('Disk cleaning is done successfully, proceed for network configuration')
    logger.info('Check if any vswitch configuration exists other than management network')
    clear_Vswitch_status = vm_obj.clear_Vswitch1()
    
    # if clear_Vswitch is pass proceed with creation of switch
    if clear_Vswitch_status:
        status = vm_obj.create_59_network1(vswitchname, portgroupname, uplinks)
        if status:
            logger.info('successfully created')            
    
    logger.info('Cleaning of data disks and network creation completed... Proceed with VM deployment')
    
    logger.info('Check if OVFTool already presented on appliance')
    app_obj.check_and_install_ovf_tool(share_obj)
    logger.info('Mount {} on appliance to get vms'.format(Applnce_MOUNT_DIR))
    app_obj.create_share_mount_point(MOUNT_IP, Applnce_MOUNT_DIR)

    mount_VM_dir = posixpath.join(Applnce_MOUNT_DIR, esx_image_path)
    logger.info('mount_VM_dir is {}'.format(mount_VM_dir))
    
    logger.info('getting all vm images')
    logger.info('custom_images are {} '.format(custom_images))

    all_vm_images_info = share_obj.get_vm_images_info(mount_VM_dir, custom_images)
    logger.info('all_vm_images_info is {}'.format(all_vm_images_info))
    random.shuffle(all_vm_images_info)
    
    
    n = total_vms-len(pre_configured_vms)
    extra_vm_images_info = all_vm_images_info[0:n]
    logger.info('extra_vm_images_info is {}'.format(extra_vm_images_info))
    
    vm_datastores = list()
    for datastore_name in existing_ds:
        if 'datastore' not in datastore_name:
            vm_datastores.append(datastore_name)
    for datastore_name in vm_datastores:
        if datastore_name not in existing_ds_vms_map:
            existing_ds_vms_map[datastore_name] = list()
    max_vm_count = math.ceil(total_vms/len(vm_datastores))    
    pending_vms = list()
    
    for vm_image_name, vm_image_size in extra_vm_images_info:
        vm_deployed = False
        for datastore_name in vm_datastores:
            datastore_free_space = vm_obj.get_datastore_size(datastore_name)
            if datastore_free_space and datastore_free_space > 2 * vm_image_size and len(existing_ds_vms_map[datastore_name]) < max_vm_count:
                vm_image_abs_path = posixpath.join(mount_VM_dir, vm_image_name)
                datastore_abs_path = posixpath.join(DestComDirPath, datastore_name)
                logger.info('vm_image_abs_path and datastore_abs_path is {} {}'.format(vm_image_abs_path, datastore_abs_path))
                sourceType = 'VMX'
                #logger.info('sourceType is {}'.format(sourceType))
                # logger.info(sourceType,datastore_name,portgroupname,vm_image_abs_path,host_id,share_pwd,host_IP)
                x = random.randint(0, 255)
                VM_Name = vm_image_name + str(x)    
                vm_deployed = app_obj.OVF_VM_Deploy(share_obj,sourceType, datastore_name, portgroupname, VM_Name, vm_image_abs_path, host_id, host_password, host_IP)
        if vm_deployed is False:
            pending_vms.append((vm_image_name, vm_image_size))

    if pending_vms:
        logger.warning('Following vms are not deployed')
        logger.warning('\n'.join(pending_vms))
        # return False
    else:
        logger.info("Successfully deployed all VMs")
        # return True

    logger.info('disconnecting host')
    host_system.disconnect_host()
    logger.info('disconnecting appliance')
    appliance_system.disconnect_host()
    logger.info('disconnecting share')
    share_system.disconnect_host()


    post_deployment_vms = vm_obj.get_existing_vms()
    logger.info('New_deployed_vms are {}'.format(post_deployment_vms))

    New_VM_Ips = vm_obj.get_VM_IpAddr(post_deployment_vms)
    #logger.info('VM ip list is {}'.format(New_VM_Ips))

    for vm_host_ip in New_VM_Ips:
        new_vm = RemoteSystem(vm_host_ip, vm_loginid, vm_loginpassword)
        new_vm.connect_host()

        # ls_verify = new_vm.execute_command('ls \n')
        # logger.info(ls_verify)

        cmd = "sed -i 's/pct_of_memory 30/pct_of_memory 100/g' /input_decks/stressdeck.in"
        new_vm.execute_command(cmd)
        cmd = "sed -i 's/threads 4/threads 40/g' /input_decks/stressdeck.in"
        new_vm.execute_command(cmd)
        cmd = "sed -i 's/file_size 100/file_size 1000/g' /input_decks/stressdeck.in"
        new_vm.execute_command(cmd)
        cmd = 'driver -f /input_decks/stressdeck.in -w -i &'
        new_vm.execute_command(cmd)

        stress_deck = new_vm.execute_command('cat /input_decks/stressdeck.in \n')
        print('Editing of stressdeckfile is completed and stress deck file is {}'.format(stress_deck))
        # stress_current_status=new_vm.execute_command('/std_tools/MonitorTests.pl')
        #logger.info('stress_current_status is {}'.format(stress_current_status))
        process_stress_check = new_vm.execute_command('ps -ef | grep stress \n')
        print('current running process of stress deck file is {}'.format(process_stress_check))
        new_vm.disconnect_host()
        


if __name__ == "__main__":

    logger.info("Connect to vmware host")
    host_system = RemoteSystem(host_IP, host_id, host_password)
    host_system.connect_host()

    vm_obj = VMUtils(host_system)

    logger.info('Connect to applicance')
    appliance_system = RemoteSystem(appliance_ip, appliance_id, appliance_pwd)
    appliance_system.connect_host()

    app_obj = ApplianceUtils(appliance_system)

    logger.info("Connect to share to retrive vm template files")
    share_system = RemoteSystem(share_ip, share_username, share_pwd)
    share_system.connect_host()

    share_obj = ShareUtils(share_system)
    #AUL_upgrade()
    #AUL_install()
    #check_mpmSpeed=vm_obj.set_sync_speed()
    logger.info('getting existing datastores')
    existing_ds = vm_obj.get_existing_datastores()
    logger.info('existing Data store are {}'.format(existing_ds))
    
    check_sync_status=vm_obj.check_sync_status()
    logger.info(check_sync_status)
    #logger.info('creating new datastores if possible')
    #Create_Mpms=app_obj.create_new_ds()
    #vib_install()
    #vib_uninstall()
    #AUL_upgrade()
    #cleanUP()
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('--images')
    args = parser.parse_args()
    user_images = args.images.split(',') if args.images else None
    run_vm_stress_test(user_images, 3)
    '''

       
	
   
