import xmlrpc.client
from models import Warehouse, Product, Transfer
# Remove the circular import:
# from create_transfer import create_transfer
from create_entry import create_entry
from config import url, db, username, password, uid, TransferError, Producto
from datetime import datetime, timedelta
import time

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

def get_recent_transfers(limit=15, warehouse_filter=None):
    """
    Retrieve the most recent internal transfers between locations.
    Filters out references that:
    - Start with "PRB"
    - Start with "AVE"
    - Contain "/POS"
    
    Can filter by warehouse name (origin or destination)
    
    Args:
        limit: The maximum number of transfers to retrieve (default: 15)
        warehouse_filter: Optional warehouse name to filter by (default: None)
        
    Returns:
        A list of simplified transfer objects
    """
    try:
        if not uid:
            return []
            
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        
        # Initial batch size and offset for pagination
        batch_size = max(limit * 2, 30)
        offset = 0
        max_attempts = 5
        attempts = 0
        filtered_pickings = []
        
        # If warehouse filter is provided, first get the location IDs for that warehouse
        location_domain = []
        if warehouse_filter and warehouse_filter != "Todos":
            # First find the warehouse ID by name
            warehouse_ids = models.execute_kw(db, uid, password, 'stock.warehouse', 'search', 
                [[('name', '=', warehouse_filter)]])
            
            if warehouse_ids:
                # Get all stock locations for this warehouse
                warehouse_locations = models.execute_kw(db, uid, password, 'stock.location', 'search', 
                    [[('warehouse_id', '=', warehouse_ids[0])]])
                
                if warehouse_locations:
                    # Create domain filter: origin OR destination matches any warehouse location
                    location_domain = ['|', 
                        ('location_id', 'in', warehouse_locations), 
                        ('location_dest_id', 'in', warehouse_locations)
                    ]
        
        # Keep fetching batches until we have enough transfers or reach max attempts
        while len(filtered_pickings) < limit and attempts < max_attempts:
            attempts += 1
            
            # Combine filter domains
            domain = [('state', '=', 'done')]
            if location_domain:
                domain.extend(location_domain)
            
            # Get a batch of transfers with the combined domain filter
            current_batch = models.execute_kw(db, uid, password, 'stock.picking', 'search_read', 
                [domain],
                {
                    'fields': ['id', 'name', 'date', 'location_id', 'location_dest_id', 'origin', 'state', 'scheduled_date', 'date_done'],
                    'order': 'date desc', 
                    'limit': batch_size,
                    'offset': offset
                }
            )
            
            if not current_batch:
                break
                
            # Filter current batch
            for picking in current_batch:
                reference = picking.get('name', '')
                
                # Skip transfers with references that match the filter criteria
                if (reference and 
                    (reference.startswith("PRB") or 
                     reference.startswith("AVE") or 
                     "/POS" in reference)):
                    continue
                
                # Include this transfer
                filtered_pickings.append(picking)
                
                # If we have enough transfers, stop adding more
                if len(filtered_pickings) >= limit:
                    break
            
            # Update offset for next batch
            offset += batch_size
            
            # If we processed an entire batch but still don't have enough,
            # double the batch size for the next fetch to speed up the process
            if len(filtered_pickings) < limit:
                batch_size *= 2
        
        # Truncate to exactly the limit
        pickings = filtered_pickings[:limit]
        
        # No need to continue if we filtered out all the transfers
        if not pickings:
            return []
        
        # Extract all location IDs to fetch them in a batch
        location_ids = []
        for picking in pickings:
            location_ids.append(picking['location_id'][0])
            location_ids.append(picking['location_dest_id'][0])
        
        # Remove duplicates
        location_ids = list(set(location_ids))
        
        # Fetch all locations data in a single query
        locations = {}
        if location_ids:
            location_data = models.execute_kw(db, uid, password, 'stock.location', 'read', 
                [location_ids], {'fields': ['id', 'name', 'display_name', 'complete_name']}
            )
            for loc in location_data:
                locations[loc['id']] = {
                    'name': loc['name'],
                    'display_name': loc['display_name'],
                    'complete_name': loc.get('complete_name', loc['name'])
                }
        
        # Collect all picking IDs for fetching move lines
        picking_ids = [p['id'] for p in pickings]
        
        # Get all move lines for all pickings in a single query
        move_lines = models.execute_kw(db, uid, password, 'stock.move', 'search_read', 
            [[('picking_id', 'in', picking_ids)]], 
            {'fields': ['picking_id', 'product_id', 'quantity_done', 'product_uom_qty', 'state', 'priority']}
        )
        
        # Group move lines by picking_id
        moves_by_picking = {}
        for move in move_lines:
            picking_id = move['picking_id'][0]
            if picking_id not in moves_by_picking:
                moves_by_picking[picking_id] = []
            moves_by_picking[picking_id].append(move)
        
        # Get all product IDs from moves
        product_ids = [move['product_id'][0] for move in move_lines]
        product_ids = list(set(product_ids))  # Remove duplicates
        
        # Fetch all products data in a single query
        products_dict = {}
        if product_ids:
            products_data = models.execute_kw(db, uid, password, 'product.product', 'read', 
                [product_ids], {'fields': ['id', 'name', 'default_code', 'type', 'categ_id', 'uom_id']}
            )
            for prod in products_data:
                products_dict[prod['id']] = {
                    'name': prod['name'],
                    'default_code': prod.get('default_code', ''),
                    'type': prod.get('type', 'product'),
                    'category_id': prod.get('categ_id', [0, 'Unknown'])[0] if isinstance(prod.get('categ_id'), list) else None,
                    'uom_id': prod.get('uom_id', [0, 'Units'])[0] if isinstance(prod.get('uom_id'), list) else None
                }
        
        # Now build the transfers with all the pre-fetched data
        transfers = []
        for picking in pickings:
            try:
                # Format dates with timezone adjustment (UTC to local timezone UTC-5)
                date_done = None
                scheduled_date = None
                
                try:
                    if picking.get('date'):
                        # Parse date from Odoo (in UTC)
                        date_obj = datetime.strptime(picking['date'], "%Y-%m-%d %H:%M:%S")
                        # Adjust for timezone difference (UTC to UTC-5)
                        local_date_obj = date_obj - timedelta(hours=5)
                        # Format with AM/PM
                        formatted_date = local_date_obj.strftime("%Y-%m-%d %I:%M:%S %p")
                except:
                    formatted_date = picking.get('date', 'N/A')
                    
                try:
                    if picking.get('date_done'):
                        # Parse date from Odoo (in UTC)
                        date_done_obj = datetime.strptime(picking['date_done'], "%Y-%m-%d %H:%M:%S")
                        # Adjust for timezone difference (UTC to UTC-5)
                        local_date_done_obj = date_done_obj - timedelta(hours=5)
                        # Format with AM/PM
                        date_done = local_date_done_obj.strftime("%Y-%m-%d %I:%M:%S %p")
                except:
                    date_done = picking.get('date_done', 'N/A')
                    
                try:
                    if picking.get('scheduled_date'):
                        # Parse date from Odoo (in UTC)
                        scheduled_date_obj = datetime.strptime(picking['scheduled_date'], "%Y-%m-%d %H:%M:%S")
                        # Adjust for timezone difference (UTC to UTC-5)
                        local_scheduled_date_obj = scheduled_date_obj - timedelta(hours=5)
                        # Format with AM/PM
                        scheduled_date = local_scheduled_date_obj.strftime("%Y-%m-%d %I:%M:%S %p")
                except:
                    scheduled_date = picking.get('scheduled_date', 'N/A')
                
                # Get source and destination from pre-fetched locations
                src_loc_id = picking['location_id'][0]
                dst_loc_id = picking['location_dest_id'][0]
                
                src_location = locations.get(src_loc_id, {'name': 'Unknown', 'display_name': 'Unknown', 'complete_name': 'Unknown'})
                dst_location = locations.get(dst_loc_id, {'name': 'Unknown', 'display_name': 'Unknown', 'complete_name': 'Unknown'})
                
                # Use display_name which often includes the warehouse
                src_name = src_location['display_name']
                dst_name = dst_location['display_name']
                
                # Get products from pre-fetched moves
                products = {}
                picking_moves = moves_by_picking.get(picking['id'], [])
                
                for move in picking_moves:
                    product_id = move['product_id'][0]
                    product_info = products_dict.get(product_id, {'name': 'Unknown', 'default_code': ''})
                    
                    key = product_info['default_code'] or str(product_id)
                    products[key] = {
                        'id': product_id,
                        'name': product_info['name'],
                        'quantity': move.get('quantity_done', 0),
                        'planned_quantity': move.get('product_uom_qty', 0),
                        'state': move.get('state', 'unknown'),
                        'priority': move.get('priority', '0'),
                        'type': product_info.get('type', 'product'),
                        'default_code': product_info.get('default_code', '')
                    }
                
                # Create detailed transfer object
                transfer = {
                    'id': picking['id'],
                    'reference': picking.get('name', ''),
                    'date': formatted_date,
                    'date_done': date_done,
                    'scheduled_date': scheduled_date,
                    'origin_warehouse': src_name,
                    'destination_warehouse': dst_name,
                    'origin_location': src_location.get('complete_name', src_name),
                    'destination_location': dst_location.get('complete_name', dst_name),
                    'products': products,
                    'origin_document': picking.get('origin', ''),
                    'state': picking.get('state', 'unknown'),
                    'product_count': len(products)
                }
                
                transfers.append(transfer)
                
            except Exception as ex:
                continue
                
        return transfers
        
    except Exception as ex:
        import traceback
        traceback.print_exc()
        return []

def get_employees_with_pins():
    """
    Retrieves employees from Odoo along with their PINs
    
    Returns:
        A list of dictionaries with only employee names and PINs:
        - name: Employee name
        - pin: Employee PIN for authentication
    """
    try:
        if not uid:
            print("Failed to authenticate with Odoo")
            return []
            
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        
        # Get only active employees with their names and pins
        employees_data = models.execute_kw(db, uid, password, 'hr.employee', 'search_read', 
            [
                [('active', '=', True), ('pin', '!=', False)]  # Only active employees with PINs
            ],
            {
                'fields': ['name', 'pin']  # Only get name and PIN
            }
        )
        
        # Format the employee data
        employees = []
        for employee in employees_data:
            if employee.get('pin'):  # Double-check PIN exists and is not empty
                employees.append({
                    'name': employee['name'],
                    'pin': employee['pin']
                })
            
        return employees
        
    except Exception as ex:
        print(f"Error getting employees: {str(ex)}")
        return []

def get_product_stock(product_code, warehouse_name=None):
    """
    Get stock levels for a specific product in one or all warehouses.
    
    Args:
        product_code (str): The product's default_code
        warehouse_name (str, optional): Name of warehouse to check stock for. 
                                       If None, returns stock for all warehouses.
    
    Returns:
        dict: Dictionary with warehouse names as keys and stock quantities as values
              Example: {"Bodega": 10, "San Jose": 5}
    """
    try:
        if not uid:
            return {}
            
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        
        # First, get the product ID from the default_code
        product_ids = models.execute_kw(db, uid, password, 'product.product', 'search', 
            [[('default_code', '=', product_code)]])
        
        if not product_ids:
            return {}  # Product not found
            
        product_id = product_ids[0]
        
        # Get all warehouses or filter by name
        warehouse_domain = []
        if warehouse_name:
            warehouse_domain = [('name', '=', warehouse_name)]
            
        warehouse_ids = models.execute_kw(db, uid, password, 'stock.warehouse', 'search', 
            [warehouse_domain])
            
        if not warehouse_ids:
            return {}  # No matching warehouses found
            
        # Get warehouses with their names for reference
        warehouses = models.execute_kw(db, uid, password, 'stock.warehouse', 'read', 
            [warehouse_ids], {'fields': ['id', 'name', 'lot_stock_id']})
            
        # Create a dictionary to store results
        stock_by_warehouse = {}
        
        # For each warehouse, get the stock quantity
        for wh in warehouses:
            wh_name = wh['name']
            stock_location_id = wh['lot_stock_id'][0]
            
            # Get the available quantity in this location
            quant_data = models.execute_kw(db, uid, password, 'stock.quant', 'search_read', 
                [[('product_id', '=', product_id), ('location_id', '=', stock_location_id)]],
                {'fields': ['quantity', 'available_quantity']}
            )
            
            # Sum quantities from all quants
            total_qty = sum(q.get('available_quantity', 0) for q in quant_data)
            
            # Store in result dict
            stock_by_warehouse[wh_name] = total_qty
            
        return stock_by_warehouse
        
    except Exception as ex:
        import traceback
        traceback.print_exc()
        print(f"Error fetching product stock: {str(ex)}")
        return {}

def get_products_stock(product_codes, warehouse_names=None):
    """
    Get stock levels for multiple products across one or more warehouses.
    
    Args:
        product_codes (list): List of product default_codes
        warehouse_names (list, optional): List of warehouse names to check stock for.
                                         If None, returns stock for all warehouses.
    
    Returns:
        dict: Dictionary with product codes as keys and warehouse stock as sub-dictionaries
              Example: {"ABC123": {"Bodega": 10, "San Jose": 5}}
    """
    try:
        if not uid:
            return {}
            
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        
        # Get product IDs from default_codes
        product_domain = [('default_code', 'in', product_codes)]
        product_data = models.execute_kw(db, uid, password, 'product.product', 'search_read', 
            [product_domain],
            {'fields': ['id', 'default_code']}
        )
        
        if not product_data:
            return {}  # No products found
            
        # Map product IDs to their default_codes
        product_map = {p['id']: p['default_code'] for p in product_data if p.get('default_code')}
        product_ids = list(product_map.keys())
        
        # Get warehouse data
        warehouse_domain = []
        if warehouse_names:
            warehouse_domain = [('name', 'in', warehouse_names)]
            
        warehouse_data = models.execute_kw(db, uid, password, 'stock.warehouse', 'search_read', 
            [warehouse_domain],
            {'fields': ['id', 'name', 'lot_stock_id']}
        )
        
        if not warehouse_data:
            return {}  # No warehouses found
            
        # Map warehouse data
        warehouse_map = {w['id']: w for w in warehouse_data}
        stock_location_ids = [w['lot_stock_id'][0] for w in warehouse_data]
        
        # Get all quants for these products and locations in a single query
        quant_domain = [
            ('product_id', 'in', product_ids),
            ('location_id', 'in', stock_location_ids)
        ]
        quant_data = models.execute_kw(db, uid, password, 'stock.quant', 'search_read', 
            [quant_domain],
            {'fields': ['product_id', 'location_id', 'quantity']}  # Use 'quantity' for on-hand stock
        )
        
        # Process the results
        result = {code: {} for code in product_codes}  # Initialize with all requested products
        
        for quant in quant_data:
            product_id = quant['product_id'][0]
            location_id = quant['location_id'][0]
            qty = quant.get('quantity', 0)  # Use 'quantity' field for on-hand stock
            
            # Find which product and warehouse this belongs to
            product_code = product_map.get(product_id)
            
            if not product_code:
                continue  # Skip if we can't map to a product code
                
            # Find which warehouse this location belongs to
            for wh_id, wh_data in warehouse_map.items():
                if wh_data['lot_stock_id'][0] == location_id:
                    wh_name = wh_data['name']
                    
                    # Initialize or add to product's warehouse quantity
                    if wh_name not in result.get(product_code, {}):
                        result[product_code][wh_name] = qty
                    else:
                        result[product_code][wh_name] += qty
                    
                    break
        
        return result
        
    except Exception as ex:
        import traceback
        traceback.print_exc()
        print(f"Error fetching multiple products stock: {str(ex)}")
        return {}

def get_products_stock_snapshot(product_codes, warehouse_names=None):
    """
    Get current stock levels for multiple products across warehouses to use as a snapshot.
    Uses the 'quantity' field for on-hand stock.
    
    Args:
        product_codes (list): List of product default_codes
        warehouse_names (list, optional): List of warehouse names to check stock for.
                                         If None, returns stock for all warehouses.
    
    Returns:
        dict: Dictionary with product codes as keys and warehouse stock as sub-dictionaries
              Example: {"ABC123": {"Bodega": 10, "San Jose": 5}}
    """
    # Call the existing function to get the current stock levels
    return get_products_stock(product_codes, warehouse_names)

def verify_transfer_state(picking_id, max_attempts=5, delay_between_attempts=2):
    """
    Verify that a transfer (picking) has reached the 'done' state.
    
    Args:
        picking_id: The ID of the picking to check
        max_attempts: Maximum number of attempts to check (default: 5)
        delay_between_attempts: Time to wait between attempts in seconds (default: 2)
        
    Returns:
        tuple: (success, state, message)
            - success (bool): True if the transfer is in 'done' state, False otherwise
            - state (str): The current state of the transfer
            - message (str): A descriptive message about the result
    """
    if not uid:
        return False, "unknown", "No se pudo autenticar con Odoo"
        
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
    
    for attempt in range(max_attempts):
        try:
            # Get the current state of the picking
            picking_data = models.execute_kw(db, uid, password, 'stock.picking', 'read', 
                [[picking_id]], {'fields': ['state', 'name']})
                
            if not picking_data:
                return False, "unknown", f"No se encontró la transferencia con ID {picking_id}"
                
            picking = picking_data[0]
            current_state = picking['state']
            picking_name = picking.get('name', str(picking_id))
            
            # Check if it's in 'done' state
            if current_state == 'done':
                return True, current_state, f"La transferencia {picking_name} se completó exitosamente (Estado: {current_state})"
            
            # If we haven't reached the max attempts, wait and try again
            if attempt < max_attempts - 1:
                time.sleep(delay_between_attempts)
            else:
                # This is the last attempt and it's still not 'done'
                state_labels = {
                    'draft': 'Borrador',
                    'waiting': 'Esperando',
                    'confirmed': 'En espera',
                    'assigned': 'Preparado',
                    'done': 'Hecho',
                    'cancel': 'Cancelado'
                }
                state_label = state_labels.get(current_state, current_state)
                return False, current_state, f"La transferencia {picking_name} no alcanzó el estado 'Hecho'. Estado actual: {state_label}"
                
        except Exception as ex:
            if attempt < max_attempts - 1:
                time.sleep(delay_between_attempts)
            else:
                return False, "error", f"Error al verificar el estado: {str(ex)}"
    
    return False, "unknown", "No se pudo determinar el estado de la transferencia"

# Create a separate function to avoid the circular import
def create_transfer_wrapper(*args, **kwargs):
    """Wrapper function to avoid circular imports"""
    # Dynamically import create_transfer only when needed
    from create_transfer import create_transfer as ct
    return ct(*args, **kwargs)

def create_entry_with_verification(warehouse_name, products):
    """
    Create an inventory entry directly without verification
    
    Args:
        warehouse_name (str): Name of the destination warehouse
        products (list): List of Producto objects with reference, quantity and cost
        
    Returns:
        dict: Result of the operation with status and details
    """
    try:
        # Call the original create_entry function directly
        result = create_entry(warehouse_name, products)
        
        # Check if an error occurred
        if isinstance(result, str) and "Error" in result:
            return {
                "success": False,
                "message": result,
                "state": "error"
            }
        
        # Create a success response
        return {
            "success": True,
            "message": f"Entrada procesada correctamente: {str(result)}",
            "result": result
        }
        
    except Exception as ex:
        return {
            "success": False,
            "message": f"Error al crear la entrada: {str(ex)}",
            "state": "error"
        }