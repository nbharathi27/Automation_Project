import posixpath
import re



from src.logger_utils.logger import get_logger

logger = get_logger(__name__)



class ShareUtils:
    def __init__(self, share_host):
        self.share_host = share_host

    def get_vm_image_size(self, vm_image_name):
        my_reg = r'(\d+)\s+' + re.escape(vm_image_name)
        cmd_output = self.share_host.execute_command('du -k "{}"'.format(vm_image_name))
        output = re.findall(my_reg, cmd_output)
        if output and output[0]:
            vm_image_size = output[0]
            #logger.info('Size of vm_image {} is {}KB'.format(vm_image_name, vm_image_size))
            return vm_image_size
        else:
            logger.info("couldn't get size of vm_image {}".format(vm_image_name))
            return False

    def get_vm_images_info(self, vmpath, custom_images=[]):
        '''
        returns VM templates from specified directory
        '''
        #share_client = connect_host(share_Ip, share_usrName, share_Pwd)
        vm_images = self.share_host.execute_command('ls {}'.format(vmpath))

        vm_images = vm_images.split('\n')
        vm_images = list(filter(None, vm_images))
        '''
        unfound_images = list(set(custom_images) - set(vm_images))
        if unfound_images:
            logger.info('Following images are not found in the share')
            logger.info(unfound_images)
        '''
        vm_images = list(map(lambda x: (x, self.get_vm_image_size(posixpath.join(vmpath, x))), vm_images))
        # disconnect_host(share_client)
        return vm_images