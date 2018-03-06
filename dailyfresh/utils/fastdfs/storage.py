from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings


class FastDFSStorage(Storage):

    def __init__(self, client_conf=None, server_ip=None):

        if client_conf is None:
            client_conf = settings.CLIENT_CONF
        self.client_conf = client_conf

        if server_ip is None:
            server_ip = settings.SERVER_IP
        self.server_ip = server_ip

    def _open(self, name, mode='rb'):
        """打开文件时使用的："""
        pass

    def _save(self, name, content):
        """存储文件时使用的"""
        # 创建fdfs客户client
        client = Fdfs_client(self.client_conf)

        # 获取上传文件的对象
        file_data = content.read()

        try:
            ret = client.upload_by_buffer(file_data)
        except Exception as e:
            print(e)
            raise

        """判断是否上传成功"""
        if ret.get('Status') == 'Upload successed.':
            # 上传成功，获取file_id
            file_id = ret.get('Remote file_id')
            return file_id
        else:
            # 上传失败
            raise Exception("上传文件到FDFS失败！")

    def exists(self, name):
        """判断django中该文件是否存在"""
        return False

    def url(self, name):
        return self.server_ip + name