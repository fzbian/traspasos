import xmlrpc.client
from models import Warehouse, Product
from create_transfer import create_transfer
from create_entry import create_entry
from config import url, db, username, password, uid, TransferError, Producto

def get_warehouses():
    if uid:
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        warehouses_data = models.execute_kw(db, uid, password, 'stock.warehouse', 'search_read', [[], ['id', 'name']])
        warehouses = [Warehouse(w['id'], w['name']) for w in warehouses_data]
        return warehouses
    else:
        print("Failed to authenticate with Odoo")
        return []

def get_products():
    if uid:
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        products_data = models.execute_kw(db, uid, password, 'product.product', 'search_read', [[], ['id', 'name', 'type', 'categ_id', 'list_price', 'qty_available', 'default_code']])
        products = [Product(p['id'], p['name'], p['type'], p['categ_id'][0], p['list_price'], p['qty_available'], p['default_code']) for p in products_data]
        return products
    else:
        print("Failed to authenticate with Odoo")
        return []

# Example transfer
product_transfers = {'1.1': 2}  # Example product references and quantities
result = create_transfer('Prueba', 'Averiados', product_transfers)
if isinstance(result, TransferError):
    print(f"Error: {result.message}")
else:
    print(result)

""""
productos = [
    Producto(referencia="9.9", cantidad=200, costo=15000)
]
result = create_entry('Prueba', productos)
if isinstance(result, TransferError):
    print(f"Error: {result.message}")
else:
    print(result)
"""