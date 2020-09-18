import re
import time
import posixpath

from src.constants.package_wide_constants import ovf_bin_path

from src.logger_utils.logger import get_logger

logger = get_logger(__name__)

host_prompt = r"\[root@.*?]"


class ApplianceUtils:
    def __init__(self, appliance_host):
        self.appliance_host = appliance_host

    def enable_firewall(self):
        check_Fstatus = self.appliance_host.execute_command('esxcli network firewall get')
        default_action = re.findall(r"Default Action:\s(.*)", check_Fstatus)
        if default_action and default_action[0] == "DROP":
            _ = self.appliance_host.execute_command('esxcli network firewall set --default-action true')
            new_firewall_status = self.appliance_host.execute_command('esxcli network firewall get')
            Daction = re.findall(r"Default Action:\s(.*)", new_firewall_status)
            if Daction and Daction[0] == "PASS":
                logger.info('Firewall default-action set to {}'.format(Daction[0]))
                return True
            else:
                logger.info('Firewall default-action set to {},Copy VMs not allowed'.format(Daction[0]))
                return False
        else:
            logger.info('Firewall default-action set to {},vms copy is allowed'.format(default_action[0]))
            return True

    def disable_firewall(self):
        check_Fstatus = self.appliance_host.execute_command('esxcli network firewall get')
        default_action = re.findall(r"Default Action:\s(.*)", check_Fstatus)
        if default_action and default_action[0] == "PASS":
            _ = self.appliance_host.execute_command('esxcli network firewall set --default-action false')
            new_firewall_status = self.appliance_host.execute_command('esxcli network firewall get')
            Daction = re.findall(r"Default Action:\s(.*)", new_firewall_status)
            if Daction and Daction[0] == "DROP":
                logger.info('Firewall default-action set to {}'.format(Daction[0]))
                return True
            else:
                logger.info('Firewall default-action set to {}'.format(Daction[0]))
                return False
        else:
            logger.info('Firewall default-action set to {}'.format(default_action[0]))
            return True

    def copy_vm_image(self, share_obj, SrcFilePath, DestFilepath, VMtemplateName):
        '''
        SrcDirPath: Remote path
        DestDirPath: Local path
        '''
        #logger.info('source vm image path from share is {}'.format(SrcVmImagepath))
        #logger.info('destination volume path in host system is {}'.format(DestDatastorepath))
        logger.info('Source File path is {}'.format(SrcFilePath))
        logger.info('Destination File path is {}'.format(DestFilepath))
        print('Check OS type')
        check_os_type = self.appliance_host.execute_command('uname')
        if "VM" in check_os_type and self.enable_firewall() is False:
            logger.info('firewall set is unsuccessful')
            return False
        copy_status = True
        handle = self.appliance_host.client.invoke_shell()
        handle.send('scp {}@{}:"{}{}" "{}"\n'.format(share_obj.share_host.username, share_obj.share_host.ip_address, SrcFilePath, VMtemplateName, DestFilepath))
        time.sleep(10)
        output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
        logger.info(output)

        if "yes/no" in output:
            handle.send('yes\n')
            time.sleep(1)
            output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
            logger.info(output)
        if "100%" in output:
            handle.send('\n')
            time.sleep(5)
            output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
            logger.info(output)
            copy_status = True
        if "password:" in output:
            handle.send(share_obj.share_host.password+'\n')
            time.sleep(1)
            output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
            logger.info(output)
            retries = 100
            while retries:
                retries -= 1
                output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
                logger.info(output)
                check_prompt = re.findall(host_prompt, output)
                if check_prompt:
                    logger.info("host prompt found")
                    copy_status = True
                    break
                elif 'No Such file or directory' in output:
                    logger.info("Found error as No Such file or directory")
                    break
                else:
                    logger.info('waiting for host prompt')
                    time.sleep(30)
        target_file_name = self.appliance_host.execute_command('ls "{}"'.format(DestFilepath))
        if VMtemplateName in target_file_name:
            logger.info('file Copied successfully')
        else:
            logger.errors('file copying failed')
            return False
        return copy_status
        
        

    def install_Ovf_Tool(self, command):

        logger.info('Proceed for too installation')
        logger.info('installation command is {}'.format(command))
        handle = self.appliance_host.client.invoke_shell()
        handle.send('{}\n'.format(command))
        time.sleep(20)
        output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
        logger.info(output)
        if "[yes]" in output:
            handle.send('yes\n')
            time.sleep(10)
            output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
            logger.info(output)
        if "yes/no" in output:
            handle.send('yes\n')
            time.sleep(10)
            output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
            logger.info(output)
        if "Press Enter" in output:
            handle.send('\n')
            time.sleep(10)
            output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
            logger.info(output)
        if "More:" in output:
            handle.send('\n')
            time.sleep(10)
            output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
            logger.info(output)

        if "Installtion was successful" in output:
            logger.info('tool process was successful')
            return True
        else:
            logger.info('tool process was not successful')
            return False

    def get_vm_image_size(self, vm_image_name):
        my_reg = r'(\d+)\s+' + re.escape(vm_image_name)
        cmd_output = self.appliance_host.execute_command('du -k "{}"'.format(vm_image_name))
        output = re.findall(my_reg, cmd_output)
        if output and output[0]:
            vm_image_size = output[0]
            #logger.info('Size of vm_image {} is {}KB'.format(vm_image_name, vm_image_size))
            return vm_image_size
        else:
            logger.info("couldn't get size of vm_image {}".format(vm_image_name))
            return False


    def OVF_VM_Deploy(self,share_obj,VMsourceType, DatastoreVolume, NetworkportGroup, VM_name, VMsrcPath, host_id, host_password, host_ip):
        logger.info('vm_image_path is {}'.format(VMsrcPath))
        breakpoint()
        vmx_file_info = share_obj.get_vm_images_info(VMsrcPath)
        for vmx_file, _ in vmx_file_info:
            if vmx_file.endswith('.vmtx'):
                vmx_file_path = VMsrcPath + '/' + vmx_file
                logger.info('vmx_file_path is {}'.format(vmx_file_path))
        logger.info("Deploying VM")
        #reg_VM = execute_command(client, 'vim-cmd solo/registervm "{}"'.format(vmx_file_path))
        handle = self.appliance_host.client.invoke_shell()
        command = 'ovftool --noSSLVerify --acceptAllEulas --skipManifestCheck --sourceType={} --powerOn --datastore="{}" --network="{}" --name="{}" {} vi://{}:{}@{}'.format(VMsourceType, DatastoreVolume, NetworkportGroup, VM_name, vmx_file_path, host_id, host_password, host_ip)
        logger.info('deploy command is {}'.format(command))
        #handle.send('ovftool --noSSLVerify --acceptAllEulas --skipManifestCheck --sourceType={} --powerOn --datastore="{}" --network="{}" --name="{}" {} vi://{}:syseng01!@{}'.format(VMsourceType,DatastoreVolume,NetworkportGroup,VM_name,vmx_file_path,host_id,host_password,host_ip)+'\n')
        handle.send(command+'\n')
        time.sleep(5)
        output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
        print(output, end='\r')
        copy_status = False
        retries = 100
        if "Deploying to VI" in output:
            while retries:
                retries -= 1
                output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
                print(output, end='\r')
                check_prompt = re.findall(r'Completed successfully', output)
                if check_prompt:
                    logger.info("VM deployed successfully")
                    copy_status = True
                    break
                else:
                    logger.info('waiting for VM deployment')
                    time.sleep(60)
        if copy_status:
            logger.info('vm deployment is successful')
            return True
        else:
            logger.warning('vm deployment is not successful')
            return False

    def create_new_ds(self):
        '''
        Checks if any volume to be created
        '''
        # can write a def for mpm_assist and get DS
        logger.info("Check if mpm to be created")
        handle = self.appliance_host.client.invoke_shell()
        handle.send('/opt/ft/sbin/mpm_assist \n')
        while(True):
            time.sleep(5)
            output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
            logger.info(output)
            if "Create new volume" in output and "? (y/n)" in output:
                handle.send('y\n')
                time.sleep(5)
                output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
                logger.info('output is {}'.format(output))
                continue

            if "No available disks" in output:
                handle.send('\n')
                time.sleep(5)
                output = handle.recv(50000).decode(encoding='utf_8', errors='strict')
                logger.info('output is {}'.format(output))
                break

    def check_and_install_ovf_tool(self, share_obj):
        ovf_present_status = self.appliance_host.execute_command('ls {}'.format(ovf_bin_path))
        if ovf_bin_path in ovf_present_status:
            logger.info('OVFtool already presented.. Skip installation')
        else:
            logger.info('proceed for ovf tool installation')
            ovf_src_abs_path = '/test1/Aeries/Aeries_New/auto/OVFTOOL/'
            ovftool_name = 'VMware-ovftool-4.3.0-10104578-lin.x86_64.bundle.txt'
            ovf_dest_dir = '/root'
            _ = self.copy_vm_image(share_obj, ovf_src_abs_path, ovf_dest_dir, ovftool_name)
            logger.info('Change the txt file to bundle')
            ovf_bundle_name = ovftool_name.replace('.txt', '')
            #logger.info('ovf_bundle_name {}'.format(ovf_bundle_name))
            #logger.info('mv {} {}'.format(ovftool_name,ovf_bundle_name))
            _ = self.appliance_host.execute_command('mv {} {}'.format(ovftool_name, ovf_bundle_name))
            ovf_ls = self.appliance_host.execute_command('ls {}'.format(ovf_dest_dir))
            if ovf_bundle_name in ovf_ls:
                logger.info('file renamed successfully')
                _ = self.appliance_host.execute_command('chmod 777 {}'.format(ovf_bundle_name))
                _ = self.install_Ovf_Tool('./{} --eulas-agreed --required'.format(ovf_bundle_name))
            else:
                logger.info('file rename failed')
                return

    def create_share_mount_point(self, mount_ip, mount_dir):
        #logger.info()
        logger.info('create a mount point with share')

        _ = self.appliance_host.execute_command('mkdir {}'.format(mount_dir))
        logger.info('check if VMstorage share is mounted ')
        check_present_mount = self.appliance_host.execute_command('mount | grep {}'.format(mount_ip))
        logger.info('Shares mounted in appliance is {}'.format(check_present_mount))
        if mount_ip in check_present_mount:
            logger.info('file path mounted successfully')
        else:
            logger.info('share path is not mounted')
            mount_share = self.appliance_host.execute_command('mount {} {}'.format(mount_ip, mount_dir))
            logger.info('mount_share is {}'.format(mount_share))
