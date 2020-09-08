import re
import time
import posixpath
from src.logger_utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_SWITCH = 'vSwitch0'
DestComDirPath = "/vmfs/volumes"
default_uplinks = 'vmnic_100601,vmnic_110601'

def Vswitch_parse_output(output):
    return_dict = dict()
    fetch_switch_info = False
    fetch_portgroup_info = False
    for line in output.splitlines():
        if line.strip() == '':
            continue
        match_obj = re.match(r'Switch Name', line)
        if match_obj:
            fetch_switch_info = True
            fetch_portgroup_info = False
            continue
        if fetch_switch_info:
            match_switch = re.match(r'(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)', line)
            if match_switch:
                switch_name = match_switch[1].strip()
                return_dict[switch_name] = dict()
                return_dict[switch_name]['Vswitch_name'] = match_switch[1].strip()
                #return_dict[switch_name]['num_ports'] = match_switch[2].strip()
                #return_dict[switch_name]['used_ports'] = match_switch[3].strip()
                #return_dict[switch_name]['config_ports'] = match_switch[4].strip()
                #return_dict[switch_name]['mtu'] = match_switch[5].strip()
                #return_dict[switch_name]['uplinks'] = match_switch[6].strip()
                return_dict[switch_name]['portgroups_list'] = list()
            fetch_switch_info = False
        check_portgroup_info = re.match(r'\s+PortGroup Name', line)
        if check_portgroup_info:
            fetch_portgroup_info = True
            continue
        if fetch_portgroup_info:
            match_portgroup = re.match(r'(.*?)\s+(\d+)\s+(\d+)\s+(\S+)', line)
            if match_portgroup:
                portgroup_dict = dict()
                portgroup_dict['portgroup_name'] = match_portgroup[1].strip()
                #portgroup_dict['vlan_id'] = match_portgroup[2].strip()
                #portgroup_dict['used_ports'] = match_portgroup[3].strip()
                portgroup_dict['uplinks'] = match_portgroup[4].strip()
                return_dict[switch_name]['portgroups_list'].append(portgroup_dict)
    return return_dict


class VMUtils:
    def __init__(self, vm_host):
        self.vm_host = vm_host

    def get_datastore_size(self, ds_name):
        abs_ds_path = posixpath.join(DestComDirPath, ds_name)
        my_reg = r'\S+\s+\d+\s+\d+\s+(\d+)\s+\d+%\s+' + re.escape(abs_ds_path)
        cmd_output = self.vm_host.execute_command('df -k "{}"'.format(abs_ds_path))
        output = re.findall(my_reg, cmd_output)
        if output and output[0]:
            free_space = output[0]
            logger.info('Free space in datastore {} is {}KB'.format(abs_ds_path, free_space))
            return free_space
        else:
            logger.info("couldn't get free space in datastore {}".format(abs_ds_path))
            return False

    def get_existing_datastores(self):
        '''
        returns existing datastore list
        '''
        # get datastores and append them to existing_ds
        vol_list = list()
        vol_list1 = self.vm_host.execute_command('esxcli storage vmfs extent list')
        for line in vol_list1.splitlines():
            # match_obj = re.match(r'(\S+ \(\d+\))', line)
            match_obj = re.match(r'(.*?)[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+', line)
            if match_obj:
                # vol_list.append(match_obj[1])
                vol_list.append(match_obj[1].strip())
        logger.info("Data store Volume list is :{} ".format(vol_list))
        return vol_list

    def get_existing_ds_vms_map(self):
        existing_vm_list = self.vm_host.execute_command('vim-cmd vmsvc/getallvms')
        datastore_vms_map = dict()
        for line in existing_vm_list.splitlines():
            match_obj = re.search(r'\[(.*?)\]\s+(\S+\.vmx)', line)
            # match_obj = re.search(r'\[(\S+ \(\d+\))\] (\S+\.vmx)', line)
            if match_obj:
                if 'ftSys System Management Appliance' in line:
                    logger.info('ignoring appliance datastore')
                    continue
                datastore = match_obj[1]
                vm = match_obj[2]
                if datastore not in datastore_vms_map:
                    datastore_vms_map[datastore] = list()
                datastore_vms_map[datastore].append(vm)
        logger.info("Datastore Map is {}".format(datastore_vms_map))
        return datastore_vms_map

    def get_existing_vms(self):
        existing_vm_list = self.vm_host.execute_command('vim-cmd vmsvc/getallvms')
        existing_vms = list()
        for line in existing_vm_list.splitlines():
            output = re.findall(r'^(\d+)\s+.*\[(.*?)\]\s+(\S+\.vmx)', line)
            if output:
                if 'ftSys System Management Appliance' in line:
                    logger.info('ignoring appliance datastore')
                    continue
                vm_id = output[0][0]
                datastore_name = output[0][1]
                vm_name = output[0][2]
                existing_vms.append((vm_id, datastore_name, vm_name))
        logger.info("existing vms are {}".format(existing_vms))
        return existing_vms

    def clear_vms_in_datastore(self, datastore_name):
        datastore_path = posixpath.join(DestComDirPath, datastore_name)
        cmd = 'rm -rf "{}"/*'.format(datastore_path)
        logger.info('executing the below command')
        logger.info(cmd)
        output = self.vm_host.execute_command(cmd)
        logger.info('output after deleting vm files of datastore')
        logger.info(output)

    def clear_vm_files(self, ds_name, vm_path):
        vm_image_path = posixpath.join(DestComDirPath, ds_name, vm_path)
        cmd = 'rm -rf "{}"'.format(vm_image_path)
        logger.info('executing the below command')
        logger.info(cmd)
        output = self.vm_host.execute_command(cmd)
        logger.info('output after deleting vm files of {} -> {}'.format(ds_name, vm_path))
        logger.info(output)

    def unregister_vms(self, vms_list):
        vms_unregistration = True
        for vm_id, ds_name, vm_name in vms_list:
            power_currentstate_output = self.vm_host.execute_command('vim-cmd vmsvc/power.getstate {}'.format(vm_id))
            power_state_output = re.findall(r'(Powered on)', power_currentstate_output)
            powered_off = True
            if power_state_output and power_state_output[0] == 'Powered on':
                powered_off = False
                _ = self.vm_host.execute_command('vim-cmd vmsvc/power.off {}'.format(vm_id))
                max_retries = 3
                while max_retries:
                    max_retries -= 1
                    power_currentstate_output = self.vm_host.execute_command('vim-cmd vmsvc/power.getstate {}'.format(vm_id))
                    power_state_output = re.findall(r'(Powered off)', power_currentstate_output)
                    if power_state_output and power_state_output[0] == "Powered off":
                        logger.info('Powered off the VM {}'.format(vm_id))
                        powered_off = True
                        break
                    else:
                        logger.info('Wait for 5 seconds and check again')
                        time.sleep(5)
                        continue
            if powered_off:
                _ = self.vm_host.execute_command('vim-cmd vmsvc/unregister {}'.format(vm_id))
                power_newstate_output = self.vm_host.execute_command('vim-cmd vmsvc/power.getstate {}'.format(vm_id))
                if not power_newstate_output:
                    logger.info('VM - {} unregistered successfully'.format(vm_id))
                    self.clear_vm_files(ds_name, vm_name)
                    logger.info('VM {} files cleared successfully'.format(vm_id))
                else:
                    vms_unregistration = False
                    logger.info('VM - {} unregistration unsuccessful'.format(vm_id))
            else:
                vms_unregistration = False
                logger.info('Failed to power off VM - {}'.format(vm_id))

        return vms_unregistration

    def clear_Vswitch1(self):
        logger.info('execute comamnd to get availble vswitches')
        vswitch_output = self.vm_host.execute_command('esxcfg-vswitch -l')
        logger.info('Available switch config is {}'.format(vswitch_output))
        out_dict = Vswitch_parse_output(vswitch_output)
        deleted_switch_list = list()
        return_status = True
        for vswitch in out_dict:
            logger.info('---------------------------------------------')
            if vswitch == DEFAULT_SWITCH:
                logger.info('Do not delete default switch:{}'.format(DEFAULT_SWITCH))
            else:
                # here need to check if 59switch uplinks are vmnic_100601,vmnic_110601 then only we need to delete port group and vswitch else prompt no other network found other than default
                # hence proceed with creating
                delete_switch = True
                for port_group in out_dict[vswitch]['portgroups_list']:
                    if port_group['uplinks'] == default_uplinks:
                        logger.info('Found a port group {} with default_uplinks {}'.format(port_group['portgroup_name'], default_uplinks))
                        logger.info('Delete port groups of non-default switch: {}'.format(vswitch))
                        logger.info('Delete port group : {}'.format(port_group['portgroup_name']))
                        logger.info('execute clear commands to delete {}'.format(port_group['portgroup_name']))
                        _ = self.vm_host.execute_command('esxcli network vswitch standard portgroup remove -p={} -v={}'.format(port_group['portgroup_name'], vswitch))
                    else:
                        delete_switch = False
                        logger.info('Do not delete port group/vswitch with non-default uplinks: {}'.format(port_group['portgroup_name']))
                if delete_switch:
                    logger.info('Delete non-default switch: {}'.format(vswitch))
                    _ = self.vm_host.execute_command('esxcli network vswitch standard remove -v {}'.format(vswitch))
                    deleted_switch_list.append(vswitch)

        # if we delete verify with below command again to confirm no other switch info availble
        clear_new_output = self.vm_host.execute_command('esxcfg-vswitch -l')
        logger.info(clear_new_output)
        new_dict = Vswitch_parse_output(clear_new_output)
        for deleted_switch in deleted_switch_list:
            if deleted_switch in new_dict:
                logger.info('Failed to delete switch: {}'.format(deleted_switch))
                return_status = False
            else:
                logger.info('Successfully deleted switch: {}'.format(deleted_switch))

        return return_status

    def create_59_network1(self, vswitch_name, port_group_name, uplink_list):
        logger.info('Create vswitch {}'.format(vswitch_name))
        _ = self.vm_host.execute_command('esxcli network vswitch standard add -v {}'.format(vswitch_name))
        logger.info('Create portgroup and add to vswitch {}'.format(vswitch_name))
        _ = self.vm_host.execute_command('esxcli network vswitch standard portgroup add -p={} -v={}'.format(port_group_name, vswitch_name))
        # vmnic_100601 and vmnic_110601 can hardcode
        for uplink in uplink_list:
            add_Uplinks = self.vm_host.execute_command('esxcli network vswitch standard uplink add -u={} -v={}'.format(uplink, vswitch_name))
            logger.info(add_Uplinks)
            time.sleep(5)
        logger.info('Verify new switch created successfully')
        new_output = self.vm_host.execute_command('esxcfg-vswitch -l')
        logger.info(new_output)
        new_dict = Vswitch_parse_output(new_output)
        if vswitch_name in new_dict:
            logger.info('Successfully created vswitch: {}'.format(vswitch_name))
            return True
        else:
            logger.info('Failed to create switch: {}'.format(vswitch_name))
            return False

    def get_VM_IpAddr(self, VM_list):
        vm_Ip_list = list()
        for vm_id, _, vm_name in VM_list:
            #logger.info('vm_name is {}'.format(vm_name))
            if 'W2K' in vm_name:
                logger.info('vm_name is {}, skip for now'.format(vm_name))
                continue
            else:
                # logger.info(existing_vm_list)
                existing_vm_list = self.vm_host.execute_command('vim-cmd vmsvc/get.guest {} | grep ipAdd'.format(vm_id))
                ip_address = re.search(r'ipAddress\s+=\s+\"(\d+\.\d+\.\d+\.\d+)\"', existing_vm_list)
                ip = ip_address.group(1)
                logger.info("Ip address of VM Id {} is {}".format(vm_id, ip))
                vm_Ip_list.append(ip)
        logger.info('vm ip list is {}'.format(vm_Ip_list))
        return vm_Ip_list

    def wipe_vms(self):
        logger.info('Unregistering existing VMs')
        existing_vms = self.get_existing_vms()
        clear_existing_vms = self.unregister_vms(existing_vms)
        if not clear_existing_vms:
            logger.info('All VMs cannot be cleared')
            return False
        return True

    def erase_stale_vm_files(self):
        logger.info('getting existing datastores')
        existing_ds = self.get_existing_datastores()

        logger.info('cleaning VM images in all datastores')
        offline_vm_datastores = [x for x in existing_ds if 'datastore' not in x]
        for datastore in offline_vm_datastores:
            self.clear_vms_in_datastore(datastore)
        return True

    def get_data_datastores(self):
        logger.info('getting existing datastores')
        existing_ds = self.get_existing_datastores()
        logger.info('existing Data store are {}'.format(existing_ds))

        logger.info('getting data datastores')
        data_datastores = [x for x in existing_ds if 'datastore' not in x]
        logger.info('actual data datastores are {}'.format(data_datastores))
        return data_datastores
