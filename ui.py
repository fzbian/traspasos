from nicegui import ui
from utils import get_warehouses, get_products, TransferError
import asyncio
from create_entry import create_entry, TransferError
from create_transfer import create_transfer
from config import Producto

almacenes = [w.name for w in get_warehouses()]
productos = [f"{p.default_code} - {p.name}" for p in get_products()]

class Estado:
    def __init__(self):
        self.almacen_origen = ''
        self.almacen_destino = ''
        
estado = Estado()
lineas_productos = []
page = None

def setup_page(_page):
    global page
    page = _page

def abrir_seleccion_producto():
    with ui.dialog() as dialog:
        with ui.card():
            ui.label('Seleccionar un producto').style('font-weight: bold')
            producto_seleccionado = ui.select(options=productos, label='Producto').classes('mt-2')
            cantidad = ui.number(label='Cantidad', value=1, min=1).classes('mt-2')

            def agregar_producto():
                if producto_seleccionado.value:
                    lineas_productos.append({
                        'producto': producto_seleccionado.value,
                        'cantidad': cantidad.value
                    })
                    actualizar_tabla()
                    dialog.close()

            with ui.row():
                ui.button('Agregar', on_click=agregar_producto).classes('mt-2')
                ui.button('Cancelar', on_click=dialog.close).classes('mt-2')

    dialog.open()

def eliminar_linea(index):
    del lineas_productos[index]
    actualizar_tabla()

def actualizar_tabla():
    tabla.clear()
    
    with tabla:
        with ui.row().classes('w-full'):
            ui.label('Producto').style('width: 150px; font-weight: bold')
            ui.label('Cantidad').style('width: 100px; font-weight: bold')
            ui.label('Acciones').style('width: 100px; font-weight: bold')

    for i, linea in enumerate(lineas_productos):
        with tabla:
            with ui.row().classes('w-full items-center'):
                ui.label(linea['producto']).style('width: 150px')
                ui.number(
                    value=linea['cantidad'],
                    min=1,
                    on_change=lambda e, l=linea: actualizar_cantidad(e, l)
                ).style('width: 100px')
                ui.button(icon='delete', on_click=lambda i=i: eliminar_linea(i))

    with tabla:
        ui.button('Agregar línea', on_click=abrir_seleccion_producto).classes('mt-2')

def actualizar_cantidad(event, linea):
    linea['cantidad'] = event.value

# Inicializar diálogos con estilos visibles
result_dialog = ui.dialog().classes('z-50')
error_dialog = ui.dialog().classes('z-50')

async def procesar_transferencia(dialog, loading_dialog):
    try:
        dialog.close()
        loading_dialog.clear()
        
        with loading_dialog:
            with ui.card():
                ui.label('Procesando transferencia...').style('font-weight: bold')
                ui.spinner()
        
        loading_dialog.open()
        print("Loading dialog opened")

        product_transfers = {linea['producto'].split(' - ')[0]: linea['cantidad'] for linea in lineas_productos}
        result = await asyncio.to_thread(create_transfer, estado.almacen_origen, estado.almacen_destino, product_transfers)
        print("Transfer created")

        loading_dialog.clear()
        print("Loading dialog cleared")

        with loading_dialog:
            with ui.card():
                if isinstance(result, str) and result.startswith("Error en la transferencia"):
                    ui.label(result).style('color: red; font-weight: bold')
                else:
                    ui.label('Transferencia registrada exitosamente').style('color: green; font-weight: bold')
                    lineas_productos.clear()
                    actualizar_tabla()
                ui.button('Cerrar', on_click=loading_dialog.close).classes('mt-2')

        print("Result dialog updated")

    except Exception as e:
        loading_dialog.clear()
        with loading_dialog:
            with ui.card():
                ui.label(f"Error inesperado: {str(e)}").style('color: red; font-weight: bold')
                ui.button('Cerrar', on_click=loading_dialog.close).classes('mt-2')
        loading_dialog.open()

def realizar_accion():
    if not estado.almacen_origen or not estado.almacen_destino:
        ui.notify('Debe seleccionar almacenes de origen y destino', type='warning')
        return
    
    if not lineas_productos:
        ui.notify('Debe agregar al menos un producto', type='warning')
        return
    
    if estado.almacen_origen == estado.almacen_destino:
        ui.notify('Los almacenes de origen y destino deben ser diferentes', type='warning')
        return

    confirmation_dialog = ui.dialog()
    loading_dialog = ui.dialog()
    
    with confirmation_dialog:
        with ui.card():
            ui.label('Confirmar Transferencia').style('font-weight: bold')
            ui.label(f'Almacén de origen: {estado.almacen_origen}')
            ui.label(f'Almacén de destino: {estado.almacen_destino}')
            ui.label('Productos:')
            for linea in lineas_productos:
                ui.label(f"{linea['producto']}: {linea['cantidad']}")
            
            with ui.row():
                ui.button(
                    'Confirmar', 
                    on_click=lambda: asyncio.create_task(procesar_transferencia(confirmation_dialog, loading_dialog))
                ).classes('mt-2')
                ui.button('Cancelar', on_click=confirmation_dialog.close).classes('mt-2')

    with loading_dialog:
        with ui.card():
            ui.label('Procesando transferencia...').style('font-weight: bold')
            ui.spinner()

    confirmation_dialog.open()

class EstadoEntrada:
    def __init__(self):
        self.almacen = ''
        
estado_entrada = EstadoEntrada()
lineas_productos_entrada = []

def abrir_seleccion_producto_entrada():
    with ui.dialog() as dialog:
        with ui.card():
            ui.label('Seleccionar un producto').style('font-weight: bold')
            producto_seleccionado = ui.select(options=productos, label='Producto').classes('mt-2')
            cantidad = ui.number(label='Cantidad', value=1, min=1).classes('mt-2')
            costo = ui.number(label='Costo', value=0, min=0).classes('mt-2')

            def agregar_producto():
                if producto_seleccionado.value:
                    lineas_productos_entrada.append({
                        'producto': producto_seleccionado.value,
                        'cantidad': cantidad.value,
                        'costo': costo.value
                    })
                    actualizar_tabla_entrada()
                    dialog.close()

            with ui.row():
                ui.button('Agregar', on_click=agregar_producto).classes('mt-2')
                ui.button('Cancelar', on_click=dialog.close).classes('mt-2')

    dialog.open()

def eliminar_linea_entrada(index):
    del lineas_productos_entrada[index]
    actualizar_tabla_entrada()

def actualizar_tabla_entrada():
    tabla_entrada.clear()
    
    with tabla_entrada:
        with ui.row().classes('w-full'):
            ui.label('Producto').style('width: 150px; font-weight: bold')
            ui.label('Cantidad').style('width: 100px; font-weight: bold')
            ui.label('Costo').style('width: 100px; font-weight: bold')
            ui.label('Acciones').style('width: 100px; font-weight: bold')

    for i, linea in enumerate(lineas_productos_entrada):
        with tabla_entrada:
            with ui.row().classes('w-full items-center'):
                ui.label(linea['producto']).style('width: 150px')
                ui.number(
                    value=linea['cantidad'],
                    min=1,
                    on_change=lambda e, l=linea: actualizar_cantidad_entrada(e, l)
                ).style('width: 100px')
                ui.number(
                    value=linea['costo'],
                    min=0,
                    on_change=lambda e, l=linea: actualizar_costo_entrada(e, l)
                ).style('width: 100px')
                ui.button(icon='delete', on_click=lambda i=i: eliminar_linea_entrada(i))

    with tabla_entrada:
        ui.button('Agregar línea', on_click=abrir_seleccion_producto_entrada).classes('mt-2')

def actualizar_cantidad_entrada(event, linea):
    linea['cantidad'] = event.value

def actualizar_costo_entrada(event, linea):
    linea['costo'] = event.value

async def procesar_entrada(dialog, loading_dialog):
    try:
        dialog.close()
        loading_dialog.clear()
        
        with loading_dialog:
            with ui.card():
                ui.label('Procesando entrada...').style('font-weight: bold')
                ui.spinner()
        
        loading_dialog.open()
        print("Loading dialog opened")

        productos = [
            Producto(
                referencia=linea['producto'].split(' - ')[0], 
                cantidad=linea['cantidad'], 
                costo=linea['costo']
            ) for linea in lineas_productos_entrada
        ]
        result = await asyncio.to_thread(create_entry, estado_entrada.almacen, productos)

        loading_dialog.clear()
        print("Loading dialog cleared")

        with loading_dialog:
            with ui.card():
                if isinstance(result, TransferError):
                    ui.label(f"Error: {result.message}").style('color: red; font-weight: bold')
                else:
                    ui.label(result).style('color: green; font-weight: bold')
                    lineas_productos_entrada.clear()
                    actualizar_tabla_entrada()
                ui.button('Cerrar', on_click=loading_dialog.close).classes('mt-2')

        print("Result dialog updated")

    except Exception as e:
        loading_dialog.clear()
        with loading_dialog:
            with ui.card():
                ui.label(f"Error inesperado: {str(e)}").style('color: red; font-weight: bold')
                ui.button('Cerrar', on_click=loading_dialog.close).classes('mt-2')
        loading_dialog.open()

def realizar_accion_entrada():
    if not estado_entrada.almacen:
        ui.notify('Debe seleccionar un almacén', type='warning')
        return
    
    if not lineas_productos_entrada:
        ui.notify('Debe agregar al menos un producto', type='warning')
        return

    confirmation_dialog = ui.dialog()
    loading_dialog = ui.dialog()
    
    with confirmation_dialog:
        with ui.card():
            ui.label('Confirmar Entrada').style('font-weight: bold')
            ui.label(f'Almacén: {estado_entrada.almacen}')
            ui.label('Productos:')
            for linea in lineas_productos_entrada:
                ui.label(f"{linea['producto']}: {linea['cantidad']} - Costo: {linea['costo']}")
            
            with ui.row():
                ui.button(
                    'Confirmar', 
                    on_click=lambda: asyncio.create_task(procesar_entrada(confirmation_dialog, loading_dialog))
                ).classes('mt-2')
                ui.button('Cancelar', on_click=confirmation_dialog.close).classes('mt-2')

    with loading_dialog:
        with ui.card():
            ui.label('Procesando entrada...').style('font-weight: bold')
            ui.spinner()

    confirmation_dialog.open()

@ui.page('/entradas')
def entradas():
    setup_page(ui.page)
    
    with ui.card():
        ui.label('Almacén')
        ui.select(
            almacenes,
            on_change=lambda e: setattr(estado_entrada, 'almacen', e.value)
        ).classes('mb-4')

        ui.label('Productos').style('font-weight: bold')
        global tabla_entrada
        tabla_entrada = ui.column().classes('w-full')
        actualizar_tabla_entrada()

        ui.button('Registrar entrada', on_click=realizar_accion_entrada).classes('mt-4')

@ui.page('/')
def main():
    setup_page(ui.page)
    
    with ui.card():
        ui.label('Almacén de origen')
        ui.select(
            almacenes,
            on_change=lambda e: setattr(estado, 'almacen_origen', e.value)
        ).classes('mb-2')

        ui.label('Almacén de destino')
        ui.select(
            almacenes,
            on_change=lambda e: setattr(estado, 'almacen_destino', e.value)
        ).classes('mb-4')

        ui.label('Productos').style('font-weight: bold')
        global tabla
        tabla = ui.column().classes('w-full')
        actualizar_tabla()

        ui.button('Realizar transferencias', on_click=realizar_accion).classes('mt-4')

ui.run()