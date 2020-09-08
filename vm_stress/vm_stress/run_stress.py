import re
import random
import math
import argparse
import posixpath


import paramiko
import os
import time
import logging
import configparser

from src.linux_utils.remote_system import RemoteSystem
from src.linux_utils.switch_utils import SwitchUtils
from src.linux_utils.vm_utils import VMUtils
from src.linux_utils.appliance_utils import ApplianceUtils

from src.logger_utils.logger import get_logger


logger = get_logger(__name__)


vswitchname = 'cust_vSwitch1'
portgroupname = 'CustVM_PGrp'
uplinks = ['vmnic_100601', 'vmnic_110601']
# connect to host and grep available volume names, volume list needed for copying different vms on all volume
# provide static details of system and directory details

user = "root"
pw = "syseng"
esx_6 = "/VMstorage/ESX-VMTemplates/ESX6"
ESX_65 = "/VMstorage/ESX-VMTemplates/ESX-6.5"
ESX_65 = "/ESX-VMTemplates/ESX6"

host_IP = "192.168.61.222"
#host_IP = "192.168.58.41"
appliance_ip = "192.168.61.223"
#appliance_ip = "192.168.58.42"

host_password = "syseng01!"
host_password1 = "syseng01\!"
appliance_pwd = "syseng"


# number of vms required

existing_ds = list()
vm_loginid = 'root'
vm_loginpassword = 'syseng'
default_stressfile = '/input_decks/stressdeck.in'
stress_status_file = '/std_tools/MonitorTests'

MOUNT_IP = '134.111.87.198:/VMstorage'
MOUNT_DIR = '/root/vmx_template_files'

host_id = "root"
DestComDirPath = "/vmfs/volumes"


def run_vm_stress_test(custom_images, total_vms):
    logger.info("Connect to host")
    host_system = RemoteSystem(host_IP, host_id, host_password)
    host_system.connect_host()

    vm_obj = VMUtils(host_system)

    logger.info('Connect to applicance')
    appliance_system = RemoteSystem(appliance_ip, host_id, appliance_pwd)
    appliance_system.connect_host()

    app_obj = ApplianceUtils(appliance_system)

    # client = connect_host(host_IP, host_id, host_password)
    # appliance_handle = connect_host(appliance_ip, host_id, appliance_pwd)

    wipe_vms_status = vm_obj.wipe_vms()
    if wipe_vms_status is False:
        logger.error('Failed to wipe existing VMs')
        return

    erase_stale_vm_status = vm_obj.erase_stale_vm_files()
    if erase_stale_vm_status is False:
        logger.error('Failed to clean the stale VM files in datastores')
        return

    logger.info('creating new datastores if possible')
    app_obj.create_new_ds()

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
    app_obj.check_and_install_ovf_tool()

    app_obj.create_share_mount_point(MOUNT_IP, MOUNT_DIR)

    mount_VM_dir = posixpath.join(MOUNT_DIR, ESX_65)
    logger.info('mount_VM_dir is {}'.format(mount_VM_dir))

    # --------------------------------------------------------------------------------------------------------
    # --------------------------------------------------------------------------------------------------------
    logger.info('getting all vm images')
    logger.info('custom_images are {} '.format(custom_images))

    all_vm_images_info = app_obj.get_vm_images_info(mount_VM_dir, custom_images)
    #logger.info('all_vm_images_info is {}'.format(all_vm_images_info))
    random.shuffle(all_vm_images_info)
    n = total_vms-len(pre_configured_vms)
    extra_vm_images_info = all_vm_images_info[0:n]
    vm_datastores = list()
    for datastore_name in existing_ds:
        if 'datastore' not in datastore_name:
            vm_datastores.append(datastore_name)

    datastore_vms_map = dict()
    for datastore_name in vm_datastores:
        if datastore_name not in datastore_vms_map:
            datastore_vms_map[datastore_name] = list()

    max_vm_count = math.ceil(total_vms/len(vm_datastores))
    pending_vms = list()
    for vm_image_name, vm_image_size in extra_vm_images_info:
        vm_deployed = False
        for datastore_name in vm_datastores:
            datastore_free_space = vm_obj.get_datastore_size(datastore_name)
            if datastore_free_space and datastore_free_space > 2 * vm_image_size and len(datastore_vms_map[datastore_name]) < max_vm_count:
                vm_image_abs_path = posixpath.join(mount_VM_dir, vm_image_name)
                datastore_abs_path = posixpath.join(DestComDirPath, datastore_name)
                logger.info('vm_image_abs_path and datastore_abs_path is {} {}'.format(vm_image_abs_path, datastore_abs_path))
                sourceType = 'VMX'
                #logger.info('sourceType is {}'.format(sourceType))
                # logger.info(sourceType,datastore_name,portgroupname,vm_image_abs_path,host_id,share_Pwd,host_IP)
                x = random.randint(0, 255)
                VM_Name = vm_image_name + str(x)
                vm_deployed = app_obj.OVF_VM_Deploy(sourceType, datastore_name, portgroupname, VM_Name, vm_image_abs_path, host_id, host_password1, host_IP)
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
    # logger.info(sys.argv)
    parser = argparse.ArgumentParser()
    parser.add_argument('--images')
    args = parser.parse_args()
    user_images = args.images.split(',') if args.images else None
    run_vm_stress_test(user_images, 4)
