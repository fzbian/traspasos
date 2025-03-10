import xmlrpc.client
from models import Warehouse, Product, Transfer
from create_transfer import create_transfer
from create_entry import create_entry
from config import url, db, username, password, uid, TransferError, Producto
from datetime import datetime, timedelta

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

def get_recent_transfers(limit=10):
    """
    Retrieve the most recent internal transfers between locations - optimized version.
    Filters out references that:
    - Start with "PRB"
    - Start with "AVE"
    - Contain "/POS"
    
    Continues fetching until the requested limit is reached after filtering.
    
    Args:
        limit: The maximum number of transfers to retrieve (default: 10)
        
    Returns:
        A list of simplified transfer objects
    """
    try:
        if not uid:
            return []
            
        models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
        
        # Initial batch size and offset for pagination
        batch_size = limit * 2  # Start with a moderate batch size
        offset = 0
        max_attempts = 5  # Maximum number of attempts to avoid infinite loops
        attempts = 0
        filtered_pickings = []
        
        # Keep fetching batches until we have enough transfers or reach max attempts
        while len(filtered_pickings) < limit and attempts < max_attempts:
            attempts += 1
            
            # Get a batch of transfers
            current_batch = models.execute_kw(db, uid, password, 'stock.picking', 'search_read', 
                [[('state', '=', 'done')]],
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