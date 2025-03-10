import threading
import xmlrpc.client
from config import url, db, password, uid, TransferError
from messaging import send_message_to_group

def create_transfer(origin_warehouse_name, destination_warehouse_name, product_transfers):
    if uid:
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

        try:
            # Validar la existencia de los almacenes
            warehouse_ids = models.execute_kw(db, uid, password, 'stock.warehouse', 'search', [[['name', 'in', [origin_warehouse_name, destination_warehouse_name]]]])
            if len(warehouse_ids) != 2:
                raise TransferError("Alguno de los almacenes no existe.")

            warehouses = models.execute_kw(db, uid, password, 'stock.warehouse', 'read', [warehouse_ids, ['name', 'lot_stock_id']])
            origin_warehouse = next((w for w in warehouses if w['name'] == origin_warehouse_name), None)
            destination_warehouse = next((w for w in warehouses if w['name'] == destination_warehouse_name), None)

            if not origin_warehouse or not destination_warehouse:
                raise TransferError("Alguno de los almacenes no existe.")

            # Validar existencia de productos y stock
            move_lines = []
            product_details = []
            for product_ref, qty in product_transfers.items():
                if qty <= 0:
                    raise TransferError(f"La cantidad para el producto '{product_ref}' debe ser mayor que cero.")

                product_ids = models.execute_kw(db, uid, password, 'product.product', 'search', [[['default_code', '=', product_ref]]])
                if not product_ids:
                    raise TransferError(f"El producto con referencia '{product_ref}' no existe.")

                product = models.execute_kw(db, uid, password, 'product.product', 'read', [product_ids, ['name', 'id']])[0]

                stock_quant = models.execute_kw(
                    db, uid, password, 'stock.quant', 'search_read',
                    [[['product_id', '=', product['id']], ['location_id', '=', origin_warehouse['lot_stock_id'][0]]]],
                    {'fields': ['quantity']}
                )
                stock_in_origin = stock_quant[0]['quantity'] if stock_quant else 0
                print(stock_in_origin)

                if stock_in_origin < qty:
                    raise TransferError(f"No hay suficiente stock para el producto '{product_ref}' en el almacén '{origin_warehouse_name}'. "
                                        f"Requerido: {qty}, Disponible: {stock_in_origin}")

                move_lines.append((0, 0, {
                    'product_id': product['id'],
                    'product_uom_qty': qty,
                    'product_uom': 1,  # Suponiendo que el ID de la unidad de medida es 1
                    'name': product['name'],
                    'location_id': origin_warehouse['lot_stock_id'][0],
                    'location_dest_id': destination_warehouse['lot_stock_id'][0],
                }))
                product_details.append(f"[{product_ref}] {product['name']}: {qty}")

            # Crear transferencia interna
            picking_type_id = models.execute_kw(db, uid, password, 'stock.picking.type', 'search', [[['warehouse_id', '=', origin_warehouse['id']], ['code', '=', 'internal']]])
            if not picking_type_id:
                raise TransferError("No se encontró un tipo de transferencia interna.")

            picking_id = models.execute_kw(db, uid, password, 'stock.picking', 'create', [{
                'picking_type_id': picking_type_id[0],
                'location_id': origin_warehouse['lot_stock_id'][0],
                'location_dest_id': destination_warehouse['lot_stock_id'][0],
                'move_ids_without_package': move_lines
            }])

            # Confirmar y asignar la transferencia
            models.execute_kw(db, uid, password, 'stock.picking', 'action_confirm', [[picking_id]])
            models.execute_kw(db, uid, password, 'stock.picking', 'action_assign', [[picking_id]])

            # Actualizar qty_done para cada línea de movimiento
            move_lines = models.execute_kw(db, uid, password, 'stock.move.line', 'search_read', [[['picking_id', '=', picking_id]]], {'fields': ['id', 'reserved_qty']})
            for move_line in move_lines:
                models.execute_kw(db, uid, password, 'stock.move.line', 'write', [[move_line['id']], {'qty_done': move_line['reserved_qty']}])

            # Validar la transferencia
            models.execute_kw(db, uid, password, 'stock.picking', 'button_validate', [[picking_id]])

            #message = f"{origin_warehouse_name} ▶ {destination_warehouse_name}\n" + "\n".join(product_details)
            #threading.Thread(target=send_message_to_group, args=(message,)).start()
            return f"Transferencia creada y validada con éxito. ID: {picking_id}"

        except TransferError as e:
            return f"Error en la transferencia: {e.message}"
        except Exception as e:
            return f"Error inesperado: {e}"

    else:
        return TransferError("Failed to authenticate with Odoo")
