import threading
import xmlrpc.client
from config import url, db, password, uid, TransferError
from messaging import send_message_to_group
import time

# Import only what's needed from utils without creating circular dependency
from utils import verify_transfer_state

def check_stock_availability(product_code, warehouse_name, required_qty):
    """
    Check if a warehouse has enough stock of a product for the requested transfer
    
    Args:
        product_code (str): Product default code
        warehouse_name (str): Warehouse name
        required_qty (float): Required quantity for transfer
        
    Returns:
        tuple: (bool, float) - (has_enough_stock, current_qty)
    """
    try:
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        
        # Find warehouse by name
        warehouse_ids = models.execute_kw(db, uid, password, 'stock.warehouse', 'search', 
            [[('name', '=', warehouse_name)]])
            
        if not warehouse_ids:
            return False, 0
            
        warehouse_id = warehouse_ids[0]
        
        # Get stock location
        warehouse_data = models.execute_kw(db, uid, password, 'stock.warehouse', 'read', 
            [warehouse_id], {'fields': ['lot_stock_id']})
            
        stock_location_id = warehouse_data[0]['lot_stock_id'][0]
        
        # Get product ID
        product_ids = models.execute_kw(db, uid, password, 'product.product', 'search', 
            [[('default_code', '=', product_code)]])
            
        if not product_ids:
            return False, 0
            
        product_id = product_ids[0]
        
        # Check stock level - use 'quantity' field for "on hand" quantity
        quant_data = models.execute_kw(db, uid, password, 'stock.quant', 'search_read', 
            [[('product_id', '=', product_id), ('location_id', '=', stock_location_id)]],
            {'fields': ['quantity']}  # Use 'quantity' instead of 'available_quantity'
        )
        
        # Sum 'quantity' field for total on-hand stock
        on_hand_qty = sum(q.get('quantity', 0) for q in quant_data)
        
        # Compare with required quantity
        return on_hand_qty >= required_qty, on_hand_qty
        
    except Exception as ex:
        print(f"Error checking stock: {str(ex)}")
        return False, 0

def create_transfer(origin_warehouse, destination_warehouse, products):
    """
    Create a new transfer from one warehouse to another
    
    Args:
        origin_warehouse (str): Name of the origin warehouse
        destination_warehouse (str): Name of the destination warehouse
        products (dict): Dictionary with product codes as keys and quantities as values
        
    Returns:
        str: Message indicating success or failure
    """
    try:
        if not uid:
            return "Error: No se pudo autenticar con Odoo"
            
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        
        # Find warehouse IDs by name
        origin_warehouse_ids = models.execute_kw(db, uid, password, 'stock.warehouse', 'search', 
            [[('name', '=', origin_warehouse)]])
            
        destination_warehouse_ids = models.execute_kw(db, uid, password, 'stock.warehouse', 'search', 
            [[('name', '=', destination_warehouse)]])
            
        if not origin_warehouse_ids:
            return f"Error: No se encontró el almacén de origen '{origin_warehouse}'"
            
        if not destination_warehouse_ids:
            return f"Error: No se encontró el almacén de destino '{destination_warehouse}'"
            
        # Validate stock availability for all products before proceeding
        unavailable_products = []
        for code, quantity in products.items():
            has_stock, available = check_stock_availability(code, origin_warehouse, quantity)
            if not has_stock:
                product_data = models.execute_kw(db, uid, password, 'product.product', 'search_read',
                    [[('default_code', '=', code)]], {'fields': ['name']})
                
                product_name = product_data[0]['name'] if product_data else code
                unavailable_products.append(f"{code} - {product_name} (Solicitado: {quantity}, Disponible: {available})")
        
        # If any product doesn't have enough stock, return error
        if unavailable_products:
            error_message = "Error: Stock insuficiente en el almacén de origen para los siguientes productos:\n"
            error_message += "\n".join(f"• {p}" for p in unavailable_products)
            return error_message
            
        # Get warehouse locations
        origin_data = models.execute_kw(db, uid, password, 'stock.warehouse', 'read', 
            [origin_warehouse_ids[0]], {'fields': ['lot_stock_id']})
            
        destination_data = models.execute_kw(db, uid, password, 'stock.warehouse', 'read', 
            [destination_warehouse_ids[0]], {'fields': ['lot_stock_id']})
            
        origin_location_id = origin_data[0]['lot_stock_id'][0]
        destination_location_id = destination_data[0]['lot_stock_id'][0]
        
        # Get product IDs from default_codes
        product_ids = {}
        for code in products:
            product_data = models.execute_kw(db, uid, password, 'product.product', 'search_read',
                [[('default_code', '=', code)]], {'fields': ['id']})
                
            if not product_data:
                return f"Error: No se encontró el producto con código '{code}'"
                
            product_ids[code] = product_data[0]['id']
        
        # Create a new stock picking
        picking_type = 'internal'  # This is an internal transfer
        
        # Get corresponding picking type ID
        picking_type_data = models.execute_kw(db, uid, password, 'stock.picking.type', 'search_read',
            [[('code', '=', picking_type), ('default_location_src_id', '=', origin_location_id)]],
            {'fields': ['id']})
            
        if not picking_type_data:
            # Try to find any internal picking type if the specific one is not found
            picking_type_data = models.execute_kw(db, uid, password, 'stock.picking.type', 'search_read',
                [[('code', '=', picking_type)]], {'fields': ['id']})
            
        if not picking_type_data:
            return "Error: No se encontró un tipo de operación adecuado para el traslado"
            
        picking_type_id = picking_type_data[0]['id']
        
        # Create the picking (transfer)
        picking_values = {
            'location_id': origin_location_id,
            'location_dest_id': destination_location_id,
            'picking_type_id': picking_type_id,
            'origin': f'Transferencia desde {origin_warehouse} a {destination_warehouse}'
        }
        
        picking_id = models.execute_kw(db, uid, password, 'stock.picking', 'create', [picking_values])
        
        # Create stock moves for each product
        for code, quantity in products.items():
            product_id = product_ids[code]
            
            # Get product's unit of measure
            product_data = models.execute_kw(db, uid, password, 'product.product', 'read',
                [product_id], {'fields': ['uom_id']})
            uom_id = product_data[0]['uom_id'][0]
            
            move_values = {
                'name': f'Traslado de {code}',
                'product_id': product_id,
                'product_uom': uom_id,
                'product_uom_qty': quantity,
                'picking_id': picking_id,
                'location_id': origin_location_id,
                'location_dest_id': destination_location_id
            }
            
            # Create the move
            models.execute_kw(db, uid, password, 'stock.move', 'create', [move_values])
        
        # Confirm the picking
        models.execute_kw(db, uid, password, 'stock.picking', 'action_confirm', [picking_id])
        
        # Mark as to do
        models.execute_kw(db, uid, password, 'stock.picking', 'action_assign', [picking_id])
        
        # Attempt to verify stock availability - if there's not enough stock, this may fail
        try:
            availability = models.execute_kw(db, uid, password, 'stock.picking', 'check_availability', [picking_id])
        except:
            pass  # It's ok if this fails, we'll try to force transfer
        
        # Check immediate transfer
        try:
            models.execute_kw(db, uid, password, 'stock.picking', 'action_assign', [picking_id])
        except:
            pass
        
        # Prepare stock move lines
        picking_data = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
            [[('id', '=', picking_id)]], {'fields': ['move_line_ids', 'move_ids_without_package']})
        
        move_lines = picking_data[0]['move_line_ids']
        moves = picking_data[0]['move_ids_without_package']
        
        # If no move lines were created automatically, create them
        if not move_lines:
            for move_id in moves:
                move_data = models.execute_kw(db, uid, password, 'stock.move', 'read',
                    [move_id], {'fields': ['product_id', 'product_uom_qty', 'product_uom']})
                    
                move_line_vals = {
                    'move_id': move_id,
                    'product_id': move_data[0]['product_id'][0],
                    'product_uom_id': move_data[0]['product_uom'][0],
                    'location_id': origin_location_id,
                    'location_dest_id': destination_location_id,
                    'picking_id': picking_id,
                    'qty_done': move_data[0]['product_uom_qty']
                }
                
                models.execute_kw(db, uid, password, 'stock.move.line', 'create', [move_line_vals])
        else:
            # Update existing move lines - FIX HERE: Remove 'product_uom_qty' field which doesn't exist in stock.move.line
            for line_id in move_lines:
                # Only request the product_id field which exists in stock.move.line
                line_data = models.execute_kw(db, uid, password, 'stock.move.line', 'read',
                    [line_id], {'fields': ['product_id']})
                    
                product_data = models.execute_kw(db, uid, password, 'product.product', 'read',
                    [line_data[0]['product_id'][0]], {'fields': ['default_code']})
                    
                code = product_data[0]['default_code']
                if code in products:
                    # Update qty_done
                    models.execute_kw(db, uid, password, 'stock.move.line', 'write',
                        [line_id, {'qty_done': products[code]}])
        
        # Validate the picking
        try:
            models.execute_kw(db, uid, password, 'stock.picking', 'action_done', [picking_id])
        except Exception as ex:
            # If validation fails, try to use button_validate
            try:
                models.execute_kw(db, uid, password, 'stock.picking', 'button_validate', [picking_id])
            except:
                # Log the error but continue - we'll verify status in a moment
                print(f"Error during validation: {str(ex)}")
        
        # Get picking data to include its name (reference) in the response
        picking_info = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
            [[('id', '=', picking_id)]], {'fields': ['name']})
            
        picking_name = picking_info[0]['name']
        
        # Verify the transfer reached the 'done' state
        success, state, message = verify_transfer_state(picking_id)
        
        if success:
            return f"Transferencia {picking_name} creada y completada con éxito (ID: {picking_id})"
        else:
            state_labels = {
                'draft': 'Borrador',
                'waiting': 'Esperando',
                'confirmed': 'En espera',
                'assigned': 'Preparado',
                'done': 'Hecho',
                'cancel': 'Cancelado'
            }
            state_label = state_labels.get(state, state)
            
            return f"Advertencia: La transferencia {picking_name} (ID: {picking_id}) fue creada pero está en estado {state_label}. " \
                   f"Es posible que requiera finalización manual en Odoo."
        
    except Exception as ex:
        import traceback
        traceback.print_exc()
        return f"Error al crear la transferencia: {str(ex)}"
