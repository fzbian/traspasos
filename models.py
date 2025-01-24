class Warehouse:
    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __repr__(self):
        return f"Warehouse(id={self.id}, name='{self.name}')"

# Example warehouses
example_warehouses = [
    Warehouse(1, 'Bodega'),
    Warehouse(2, 'Visto'),
    Warehouse(3, 'Lo Nuestro'),
    Warehouse(4, 'San Jose'),
    Warehouse(5, 'Gran San'),
    Warehouse(6, 'Medellin'),
    Warehouse(7, 'Averiados'),
    Warehouse(8, 'Burbuja Lo Nuestro')
]

class Product:
    def __init__(self, id, name, type, categ_id, list_price, qty_available, default_code):
        self.id = id
        self.name = name
        self.type = type
        self.categ_id = categ_id
        self.list_price = list_price
        self.qty_available = qty_available
        self.default_code = default_code

    def __repr__(self):
        return f"Product(id={self.id}, name='{self.name}', type='{self.type}', categ_id={self.categ_id}, list_price={self.list_price}, qty_available={self.qty_available}, default_code='{self.default_code}')"

class Transfer:
    def __init__(self, origin_warehouse_id, destination_warehouse_id, products):
        self.origin_warehouse_id = origin_warehouse_id
        self.destination_warehouse_id = destination_warehouse_id
        self.products = products

    def __repr__(self):
        return f"Transfer(origin_warehouse_id={self.origin_warehouse_id}, destination_warehouse_id={self.destination_warehouse_id}, products={self.products})"
