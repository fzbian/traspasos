import xmlrpc.client
from datetime import datetime, timedelta
import sys
from nicegui import ui
import requests
import threading
import json  # Add this import

# Load configuration from config.json
with open('config.json') as config_file:
    config = json.load(config_file)

url = config['url']
db = config['db']
username = config['username']
password = config['password']

common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))

def create_internal_transfer(product_ref, source_warehouse_name, dest_warehouse_name, quantity):
    # Validate warehouses
    warehouse_ids = models.execute_kw(db, uid, password, 'stock.warehouse', 'search', [[['name', 'in', [source_warehouse_name, dest_warehouse_name]]]])
    if len(warehouse_ids) != 2:
        return "Alguno de los almacenes no existe."

    warehouses = models.execute_kw(db, uid, password, 'stock.warehouse', 'read', [warehouse_ids, ['name', 'lot_stock_id']])
    source_warehouse = next((w for w in warehouses if w['name'] == source_warehouse_name), None)
    dest_warehouse = next((w for w in warehouses if w['name'] == dest_warehouse_name), None)

    if not source_warehouse or not dest_warehouse:
        return "Alguno de los almacenes no existe."

    # Validate product
    product_ids = models.execute_kw(db, uid, password, 'product.product', 'search', [[['default_code', '=', product_ref]]])
    if not product_ids:
        return "El producto no existe"

    product = models.execute_kw(db, uid, password, 'product.product', 'read', [product_ids, ['qty_available']])
    if product[0]['qty_available'] < quantity:
        return "Stock no disponible para realizar esta operacion"

    # Create internal transfer
    picking_type_id = models.execute_kw(db, uid, password, 'stock.picking.type', 'search', [[['warehouse_id', '=', source_warehouse['id']], ['code', '=', 'internal']]])
    if not picking_type_id:
        return "Tipo de transferencia interna no encontrado"

    picking_id = models.execute_kw(db, uid, password, 'stock.picking', 'create', [{
        'picking_type_id': picking_type_id[0],
        'location_id': source_warehouse['lot_stock_id'][0],
        'location_dest_id': dest_warehouse['lot_stock_id'][0],
        'move_ids_without_package': [(0, 0, {
            'product_id': product_ids[0],
            'product_uom_qty': quantity,
            'product_uom': 1,  # Assuming default UoM
            'name': product_ref,
            'location_id': source_warehouse['lot_stock_id'][0],
            'location_dest_id': dest_warehouse['lot_stock_id'][0],
        })]
    }])

    models.execute_kw(db, uid, password, 'stock.picking', 'action_confirm', [[picking_id]])
    models.execute_kw(db, uid, password, 'stock.picking', 'action_assign', [[picking_id]])

    # Set quantity done for each move line
    move_lines = models.execute_kw(db, uid, password, 'stock.move.line', 'search_read', [[['picking_id', '=', picking_id]]], {'fields': ['id', 'reserved_qty']})
    for move_line in move_lines:
        models.execute_kw(db, uid, password, 'stock.move.line', 'write', [[move_line['id']], {'qty_done': move_line['reserved_qty']}])

    try:
        models.execute_kw(db, uid, password, 'stock.picking', 'button_validate', [[picking_id]])
    except xmlrpc.client.Fault as e:
        return f"Error al validar la transferencia: {e.faultString}"

    threading.Thread(target=send_message_to_group, args=(f"*Transferencia interna*\n{source_warehouse_name} ➡ {dest_warehouse_name}\n{product_ref}: {quantity}",)).start()
    return "Transferencia interna creada y validada con éxito."

def send_message_to_group(message):
    url = 'http://137.184.137.192:3000/send-message-group'
    payload = {
        'group_name': "PRUEBAKL",
        'message': message
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return "Message sent successfully."
    else:
        return f"Failed to send message. Status code: {response.status_code}"

async def show_confirmation_dialog(product_ref: str, source_warehouse_name: str, dest_warehouse_name: str, quantity: str):
    if not product_ref or not source_warehouse_name or not dest_warehouse_name or not quantity:
        ui.notify('¡Todos los campos son obligatorios!', color='red')
        return

    try:
        quantity = int(quantity)
    except ValueError:
        ui.notify('¡La cantidad debe ser un número válido!', color='red')
        return

    with ui.dialog() as dialog, ui.card():
        ui.label(f'¿Está seguro de que desea transferir {quantity} de {product_ref} desde {source_warehouse_name} a {dest_warehouse_name}?')
        with ui.row():
            ui.button('Sí', on_click=lambda: dialog.submit('Sí'))
            ui.button('No', on_click=lambda: dialog.submit('No'))

    result = await dialog
    if result == 'Sí':
        with ui.dialog() as loading_dialog, ui.card():
            ui.label('Procesando transferencia...')
            spinner = ui.spinner(size='lg')
        loading_dialog.open()
        
        await ui.run_javascript('await new Promise(resolve => setTimeout(resolve, 100));')  # Ensure the dialog is rendered
        
        error = create_internal_transfer(product_ref, source_warehouse_name, dest_warehouse_name, quantity)
        
        loading_dialog.close()  # Ensure the dialog is closed
        
        if error == "Transferencia interna creada y validada con éxito.":
            ui.notify(error, color='green')
        else:
            ui.notify(error, color='red')
    else:
        ui.notify('Transferencia cancelada.')

@ui.page('/')
def main_page():
    ui.label('Transferencia de Almacén').style('font-size: 24px; font-weight: bold; text-align: center;')
    
    with ui.column().classes('w-full max-w-md mx-auto').style('text-align: center;'):
        ui.label('Referencia del Producto:')
        product_ref = ui.input('Referencia del Producto').props('outlined required full-width')
        
        ui.label('Almacén de Origen:')
        source_warehouse = ui.select(
            ['Bodega', 'Gran San', 'Visto', 'Lo Nuestro', 'Burbuja Lo Nuestro', 'Medellin', 'San Jose', 'Averiados'],
            label='Almacén de Origen'
        ).props('outlined required full-width')
        
        ui.label('Almacén de Destino:')
        dest_warehouse = ui.select(
            ['Bodega', 'Gran San', 'Visto', 'Lo Nuestro', 'Burbuja Lo Nuestro', 'Medellin', 'San Jose', 'Averiados'],
            label='Almacén de Destino',
        ).props('outlined required full-width')
        
        ui.label('Cantidad:')
        quantity = ui.input('Cantidad').props('outlined required number full-width')
        
        ui.button('Transferir', on_click=lambda: show_confirmation_dialog(
            product_ref.value,
            source_warehouse.value,
            dest_warehouse.value,
            quantity.value
        )).props('primary full-width')

ui.run()