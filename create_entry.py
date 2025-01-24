import xmlrpc.client
import threading
from config import url, db, password, uid, TransferError
from messaging import send_message_to_group

def create_entry(warehouse_name, productos):
    if not uid:
        raise TransferError("Authentication failed")

    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

    try:
        # Find warehouse
        warehouse_ids = models.execute_kw(db, uid, password, 'stock.warehouse', 'search', [[['name', '=', warehouse_name]]])
        if not warehouse_ids:
            raise TransferError("Almacen no encontrado")

        warehouse = models.execute_kw(db, uid, password, 'stock.warehouse', 'read', [warehouse_ids, ['name', 'lot_stock_id', 'id']])[0]

        # Find input picking type
        picking_type_ids = models.execute_kw(db, uid, password, 'stock.picking.type', 'search', [[
            ['warehouse_id', '=', warehouse['id']], 
            ['code', '=', 'incoming']
        ]])
        if not picking_type_ids:
            raise TransferError("No input picking type found")

        # Find default input location
        input_location_ids = models.execute_kw(db, uid, password, 'stock.location', 'search', [[
            ['usage', '=', 'supplier']
        ]])
        input_location = input_location_ids[0] if input_location_ids else 1

        move_lines = []
        product_details = []
        for producto in productos:
            # Validate product
            product_ids = models.execute_kw(db, uid, password, 'product.product', 'search', [[['default_code', '=', producto.referencia]]])
            if not product_ids:
                raise TransferError(f"Product '{producto.referencia}' not found")

            product = models.execute_kw(db, uid, password, 'product.product', 'read', [product_ids, ['name', 'id', 'standard_price', 'qty_available', 'uom_id']])[0]

            # Validate quantities
            if producto.cantidad <= 0 or producto.costo <= 0:
                raise TransferError(f"Costo o cantidad invalida para '{producto.referencia}'")

            # Cost averaging calculation
            cantidad_actual = max(product['qty_available'], 0)
            costo_actual = product['standard_price']
            
            nuevo_costo = ((cantidad_actual * costo_actual) + (producto.cantidad * producto.costo)) / (cantidad_actual + producto.cantidad)

            move_lines.append((0, 0, {
                'product_id': product['id'],
                'product_uom_qty': producto.cantidad,
                'quantity_done': producto.cantidad,
                'product_uom': product['uom_id'][0] if product['uom_id'] else 1,
                'name': product['name'],
                'location_id': input_location,
                'location_dest_id': warehouse['lot_stock_id'][0],
                'price_unit': producto.costo
            }))

            product_details.append(f"[{producto.referencia}] {product['name']}: {producto.cantidad}")

            # Update product standard price
            models.execute_kw(db, uid, password, 'product.product', 'write', [[product['id']], {
                'standard_price': nuevo_costo
            }])

        # Create picking
        picking_id = models.execute_kw(db, uid, password, 'stock.picking', 'create', [{
            'picking_type_id': picking_type_ids[0],
            'location_id': input_location,
            'location_dest_id': warehouse['lot_stock_id'][0],
            'move_ids_without_package': move_lines
        }])

        # Confirm, assign, and validate picking
        models.execute_kw(db, uid, password, 'stock.picking', 'action_confirm', [[picking_id]])
        models.execute_kw(db, uid, password, 'stock.picking', 'action_assign', [[picking_id]])
        models.execute_kw(db, uid, password, 'stock.picking', 'button_validate', [[picking_id]])

        message = f"Entrada a *{warehouse_name}*\n" + "\n".join(product_details)
        threading.Thread(target=send_message_to_group, args=(message,)).start()

        return f"Entrada realizada correctamente ✅."

    except Exception as e:
        return f"Error: {str(e)}"