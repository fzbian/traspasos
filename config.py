import xmlrpc.client

url = 'http://137.184.137.192:8069/'
db = 'odoo'
username = 'probot@gmail.com'
password = 'probot'

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})

class TransferError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

class Producto:
    def __init__(self, referencia: str, cantidad: int, costo: int):
        self.referencia = referencia
        self.cantidad = cantidad
        self.costo = costo

    def __repr__(self):
        return f"Producto(referencia='{self.referencia}', cantidad={self.cantidad}, costo={self.costo})"
