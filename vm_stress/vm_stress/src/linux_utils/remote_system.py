import paramiko
from src.logger_utils.logger import get_logger

logger = get_logger(__name__)


class RemoteSystem:
    def __init__(self, ip_address, username, password):
        self.client = None
        self.ip_address = ip_address
        self.username = username
        self.password = password

    def connect_host(self):
        '''
        Connect host using connect_host
        '''
        logger.info('Connect to host : {}'.format(self.ip_address))
        logger.info('with Username {}'.format(self.username))
        logger.info('with Password {}'.format(self.password))
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(self.ip_address, username=self.username, password=self.password, look_for_keys=False, allow_agent=False)
            logger.info("Successfully connected to the host {}".format(self.ip_address))
            self.client = client
            return client
        except Exception as inst:
            logger.exception('Caught exception while connecting and getting invoke shell handle')
            return None

    def disconnect_host(self):
        '''
        Procedure to disconnect to remote host with given parameters and returning the shell handle
        '''
        try:
            self.client.close()
        except Exception as inst:
            logger.exception('Caught exception while disconnecting host')

    def execute_command(self, command):
        '''
        execute given commands
        '''
        if self.client is None:
            raise ValueError('Didnot connect to host')
        try:
            logger.debug('executing below command')
            logger.debug(command)
            stdin, stdout, stderr = self.client.exec_command(command)
            readBuffer = str(stdout.read(), encoding='utf-8')
            logger.debug('returning below output')
            logger.debug(readBuffer)
            return readBuffer
        except Exception as inst:
            logger.exception('Encountered exception while executing command: {}'.format(command))
            return "NA"
