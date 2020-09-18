import time
from src.linux_utils.remote_system import RemoteSystem
from src.logger_utils.logger import get_logger

logger = get_logger(__name__)


class SwitchUtils(RemoteSystem):
    def __init__(self, ip_address, username, password):
        super(SwitchUtils, self).__init__(ip_address, username, password)

    def get_vSwitch_list(self):
        #client = connect_host(host_IP, host_id, host_password)
        run_cmd = self.execute_command(' esxcli network vswitch standard list')
        self.clear_vswitch_config()
        self.create_vSwitch()
        self.add_vSwitch_uplink()
        self.add_vSwitch_portgroup()

    def clear_vswitch_config(self):
        run_cmd3 = self.execute_command('esxcli network vswitch standard portgroup remove -p=CustVM -v=vSwitch1')
        run_cmd2 = self.execute_command('esxcli network vswitch standard uplink remove -u=vmnic_110601 -v=vSwitch1')
        run_cmd1 = self.execute_command('esxcli network vswitch standard uplink remove -u=vmnic_100601 -v=vSwitch1')
        time.sleep(5)
        run_cmd = self.execute_command('esxcli network vswitch standard remove -v vSwitch1')

    def create_vSwitch(self):
        #client = connect_host(host_IP, host_id, host_password)
        logger.info('Create a Vswitch')
        run_cmd = self.execute_command('esxcli network vswitch standard add -v vSwitch1')
        run_cmd = self.execute_command('esxcli network vswitch standard list')
        logger.info('Created a Vswitch')

    def add_vSwitch_uplink(self):
        #client = connect_host(host_IP, host_id, host_password)
        logger.info('Create Uplinks and add to vswitch1')
        run_cmd1 = self.execute_command('esxcli network vswitch standard uplink add -u=vmnic_100601 -v=vSwitch1')
        logger.info(run_cmd1)
        time.sleep(5)
        run_cmd2 = self.execute_command('esxcli network vswitch standard uplink add -u=vmnic_110601 -v=vSwitch1')
        logger.info(run_cmd2)
        run_cmd = self.execute_command('esxcli network vswitch standard list')
        logger.info(run_cmd)

    def add_vSwitch_portgroup(self):
        #client = connect_host(host_IP, host_id, host_password)
        logger.info('Create portgroup and add to vswitch1')
        run_cmd1 = self.execute_command('esxcli network vswitch standard portgroup add -p=CustVM -v=vSwitch1')
        logger.info(run_cmd1)
        run_cmd = self.execute_command('esxcli network vswitch standard list')
        logger.info(run_cmd)
        
    def set_sync_speed(self):
        logger.info ("set syncing speed of esx host")
        set_speedLimit =self.execute_command("esxcli storage mpm speedLimit  --min=500000 --max=500000")
        logger.info(set_speedLimit)
        check_mpmSpeedLimit=self.execute_command('esxcli storage mpm speedLimit')
        logger.info('MPM speed set to {}'.format(check_mpmSpeedLimit))