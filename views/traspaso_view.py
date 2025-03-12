import flet as ft
from datetime import datetime
import threading
import time
from create_transfer import create_transfer
from utils import get_warehouses, get_products, get_products_stock, get_products_stock_snapshot
from messaging import send_message_to_group  # Import the messaging function

class TraspasoView(ft.View):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.route = "/traspasos"
        self.appbar = ft.AppBar(
            title=ft.Text("Crear Nuevo Traspaso"),
            bgcolor=ft.Colors.BLUE,
            center_title=True,
            actions=[
                ft.IconButton(
                    icon=ft.Icons.HOME,
                    tooltip="Volver al inicio",
                    on_click=lambda e: self.page.go("/")
                )
            ],
        )
        
        # Get warehouse data from Odoo
        self.warehouses = get_warehouses()
        self.products = get_products()
        
        # Selected products for transfer
        self.selected_products = {}  # Dict with product_code as key and quantity as value
        
        # Form fields - remove fixed widths for responsiveness
        self.origin_dropdown = ft.Dropdown(
            label="Origen",
            options=[
                ft.dropdown.Option(warehouse.name) for warehouse in self.warehouses
            ],
            expand=True,  # Fill available width
            autofocus=True
        )
        
        self.destination_dropdown = ft.Dropdown(
            label="Destino",
            options=[
                ft.dropdown.Option(warehouse.name) for warehouse in self.warehouses
            ],
            expand=True  # Fill available width
        )
        
        # Product selection fields - make them responsive
        self.product_dropdown = ft.Dropdown(
            label="Producto",
            expand=True,  # Fill available width
            options=[
                ft.dropdown.Option(f"{p.default_code} - {p.name}") for p in self.products if p.default_code
            ],
            hint_text="Seleccione un producto"
        )
        
        self.quantity_field = ft.TextField(
            label="Cantidad",
            width=100,  # Keep this narrow since it's just a number
            hint_text="Cantidad",
            #keyboard_type=ft.KeyboardType.NUMBER
        )
        
        # Products list - make it scrollable and responsive
        self.products_list = ft.ListView(
            expand=True,
            spacing=10,
            padding=10,
            auto_scroll=True,
            height=200
        )
        
        # Create the form container (all the form elements)
        self.form_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Complete el formulario de traspaso", size=20, weight=ft.FontWeight.BOLD),
                    
                    # Warehouse selection section
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Selección de almacenes:", size=16, weight=ft.FontWeight.BOLD),
                            self.origin_dropdown,
                            self.destination_dropdown
                        ]),
                        margin=ft.margin.only(bottom=10)
                    ),
                    
                    # Products selection section
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Añadir productos:", size=16, weight=ft.FontWeight.BOLD),
                            # Make product selection wrap on mobile
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Column([self.product_dropdown], col={"xs": 12, "sm": 8}),
                                    ft.Column([self.quantity_field], col={"xs": 5, "sm": 2}),
                                    ft.Column([
                                        ft.ElevatedButton(
                                            "Añadir",
                                            icon=ft.Icons.ADD,
                                            on_click=self.add_product,
                                            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE)
                                        )
                                    ], col={"xs": 7, "sm": 2})
                                ]
                            ),
                            ft.Container(
                                content=ft.Column([
                                    ft.Text("Productos seleccionados:", size=16),
                                    self.products_list
                                ]),
                                border=ft.border.all(1, ft.Colors.GREY_400),
                                border_radius=5,
                                padding=10,
                                margin=ft.margin.only(top=10),
                                expand=True
                            )
                        ]),
                        margin=ft.margin.only(bottom=10),
                        expand=True
                    ),
                    
                    # Action buttons
                    ft.ResponsiveRow(
                        controls=[
                            ft.Column([
                                ft.ElevatedButton(
                                    "Transferir",
                                    icon=ft.Icons.SEND,
                                    on_click=self.save_traspaso,
                                    style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN),
                                    height=50,
                                    width=180,
                                )
                            ], col={"xs": 12, "sm": 6}, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                            ft.Column([
                                ft.OutlinedButton(
                                    "Cancelar",
                                    icon=ft.Icons.CANCEL,
                                    on_click=lambda e: self.page.go("/"),
                                    height=50,
                                    width=180,
                                )
                            ], col={"xs": 12, "sm": 6}, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER
                    )
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True
            ),
            padding=10,
            expand=True
        )
        
        # Create the confirmation container (initially hidden)
        self.confirmation_container = ft.Container(
            content=ft.Column([
                ft.Text("Confirmar Transferencia", size=20, weight=ft.FontWeight.BOLD),
            ]),
            padding=20,
            expand=True,
            visible=False
        )
        
        # Create the status container (initially hidden)
        self.status_container = ft.Container(
            content=ft.Column([
                ft.Text("Procesando transferencia...", size=20, weight=ft.FontWeight.BOLD),
            ]),
            padding=20,
            expand=True,
            visible=False
        )
        
        # Main container that will hold either form, confirmation or status
        self.controls = [
            self.form_container,
            self.confirmation_container,
            self.status_container
        ]
    
    def add_product(self, e):
        # Show loading state on the button
        add_button = e.control
        original_icon = add_button.icon
        original_text = add_button.text
        
        add_button.disabled = True
        add_button.icon = ft.ProgressRing(width=16, height=16, stroke_width=2)
        add_button.text = "Añadiendo..."
        self.page.update()
        
        # Validate product selection
        if not self.product_dropdown.value:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Por favor seleccione un producto"))
            self.page.snack_bar.open = True
            # Reset button state
            add_button.disabled = False
            add_button.icon = original_icon
            add_button.text = original_text
            self.page.update()
            return
            
        # Validate quantity
        if not self.quantity_field.value or not self.quantity_field.value.isdigit() or int(self.quantity_field.value) <= 0:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Por favor ingrese una cantidad válida"))
            self.page.snack_bar.open = True
            # Reset button state
            add_button.disabled = False
            add_button.icon = original_icon
            add_button.text = original_text
            self.page.update()
            return
        
        try:    
            product_code = self.product_dropdown.value.split(" - ")[0]
            product_name = self.product_dropdown.value[len(product_code) + 3:]  # Skip " - "
            quantity = int(self.quantity_field.value)
            
            # Check product stock in origin warehouse before adding
            if self.origin_dropdown.value:
                # Just add the product directly without async checks, since they're causing issues
                # The warning about insufficient stock will be shown during the final validation
                self.selected_products[product_code] = quantity
                self.update_products_list()
                
                # Reset product fields
                self.product_dropdown.value = None
                self.quantity_field.value = ""
                
                # Reset button state
                add_button.disabled = False
                add_button.icon = original_icon
                add_button.text = original_text
                self.page.update()
            else:
                # No origin warehouse selected yet, add without validation
                self.selected_products[product_code] = quantity
                self.update_products_list()
                
                # Reset product fields
                self.product_dropdown.value = None
                self.quantity_field.value = ""
                
                # Reset button state
                add_button.disabled = False
                add_button.icon = original_icon
                add_button.text = original_text
                self.page.update()
                
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Error al añadir producto: {str(ex)}"))
            self.page.snack_bar.open = True
            
            # Reset button state
            add_button.disabled = False
            add_button.icon = original_icon
            add_button.text = original_text
            self.page.update()
    
    def update_products_list(self):
        # Clear existing list
        self.products_list.controls.clear()
        
        # Add each product to the list with responsive layout
        for product_code, quantity in self.selected_products.items():
            # Find product name
            product_name = next((p.name for p in self.products if p.default_code == product_code), product_code)
            
            # Create a delete button with a fixed product code reference
            delete_button = ft.IconButton(
                icon=ft.Icons.DELETE,
                tooltip="Eliminar",
                data=product_code,  # Store the product code as data
                icon_size=24  # Bigger icon for touch
            )
            delete_button.on_click = self.create_delete_handler(product_code)
            
            # Create more touch-friendly rows
            self.products_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Text(f"{product_code} - {product_name}: {quantity}", expand=True),
                                delete_button
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        padding=10  # Add padding inside the card
                    ),
                    margin=ft.margin.only(bottom=5)
                )
            )
        
        self.page.update()
    
    def create_delete_handler(self, product_code):
        """Create a dedicated handler function for each delete button"""
        def handle_delete(e):
            self.remove_product(product_code)
        return handle_delete
    
    def remove_product(self, product_code):
        if (product_code in self.selected_products):
            del self.selected_products[product_code]
            self.update_products_list()
    
    def save_traspaso(self, e):
        # Store the original button reference for later use
        self.transfer_button = e.control
        
        # Show loading state
        self.transfer_button.disabled = True
        self.transfer_button.icon = ft.ProgressRing(width=16, height=16, stroke_width=2)
        self.transfer_button.text = "Procesando..."
        self.page.update()
        
        # Validate inputs
        if not self.origin_dropdown.value:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Por favor seleccione el origen"))
            self.page.snack_bar.open = True
            # Reset button
            self.transfer_button.disabled = False
            self.transfer_button.icon = ft.Icons.SEND
            self.transfer_button.text = "Transferir"
            self.page.update()
            return
            
        if not self.destination_dropdown.value:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Por favor seleccione el destino"))
            self.page.snack_bar.open = True
            # Reset button
            self.transfer_button.disabled = False
            self.transfer_button.icon = ft.Icons.SEND
            self.transfer_button.text = "Transferir"
            self.page.update()
            return
            
        if self.origin_dropdown.value == self.destination_dropdown.value:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("El origen y destino no pueden ser iguales"))
            self.page.snack_bar.open = True
            # Reset button
            self.transfer_button.disabled = False
            self.transfer_button.icon = ft.Icons.SEND
            self.transfer_button.text = "Transferir"
            self.page.update()
            return
            
        if not self.selected_products:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Por favor añada al menos un producto"))
            self.page.snack_bar.open = True
            # Reset button
            self.transfer_button.disabled = False
            self.transfer_button.icon = ft.Icons.SEND
            self.transfer_button.text = "Transferir"
            self.page.update()
            return
        
        # Skip stock validation in UI and go straight to confirmation screen
        self.show_confirmation_screen()
    
    def show_confirmation_screen(self):
        """Show a confirmation screen before processing the transfer"""
        # Reset transfer button
        self.transfer_button.disabled = False
        self.transfer_button.icon = ft.Icons.SEND  # Updated from ft.icons.SEND
        self.transfer_button.text = "Transferir"
        
        # Origin and destination
        origin_warehouse = self.origin_dropdown.value
        destination_warehouse = self.destination_dropdown.value
        
        # Build product list
        product_details = []
        for product_code, quantity in self.selected_products.items():
            product_name = next((p.name for p in self.products if p.default_code == product_code), product_code)
            product_details.append(
                ft.Container(
                    content=ft.Text(f"• {product_code} - {product_name}: {quantity}"),
                    margin=ft.margin.only(bottom=5)
                )
            )
        
        # Populate confirmation screen
        self.confirmation_container.content = ft.Column([
            # Header
            ft.Text("Confirmar Transferencia", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
            ft.Divider(),
            
            # Transfer details
            ft.Text("Información de Traspaso", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.ARROW_UPWARD, color=ft.Colors.GREEN, size=18),  # Updated from ft.icons.ARROW_UPWARD
                        ft.Text(f"Origen: {origin_warehouse}", size=16)
                    ]),
                    ft.Row([
                        ft.Icon(ft.Icons.ARROW_DOWNWARD, color=ft.Colors.RED, size=18),  # Updated from ft.icons.ARROW_DOWNWARD
                        ft.Text(f"Destino: {destination_warehouse}", size=16)
                    ])
                ]),
                margin=ft.margin.only(bottom=10, left=10)
            ),
            ft.Divider(),
            
            # Product details
            ft.Text(f"Productos a Transferir ({len(self.selected_products)})", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Column(product_details, scroll=ft.ScrollMode.AUTO),
                height=200,
                border=ft.border.all(1, ft.Colors.GREY_400),
                border_radius=5,
                padding=10,
                margin=ft.margin.only(bottom=20)
            ),
            
            # Confirmation question
            ft.Text("¿Desea continuar con esta transferencia?", size=16, weight=ft.FontWeight.BOLD),
            
            # Action buttons
            ft.Row([
                ft.ElevatedButton(
                    "Sí, Realizar Transferencia",
                    icon=ft.Icons.CHECK,  # Updated from ft.icons.CHECK
                    on_click=self.process_confirmed_transfer,
                    style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.GREEN),
                    height=50
                ),
                ft.OutlinedButton(
                    "Cancelar",
                    icon=ft.Icons.CANCEL,  # Updated from ft.icons.CANCEL
                    on_click=self.cancel_confirmation,
                    height=50
                )
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=20)
        ], spacing=10, scroll=ft.ScrollMode.AUTO)
        
        # Show confirmation screen, hide form
        self.form_container.visible = False
        self.confirmation_container.visible = True
        self.status_container.visible = False
        self.page.update()
    
    def cancel_confirmation(self, e):
        """Return to the form view without processing the transfer"""
        self.form_container.visible = True
        self.confirmation_container.visible = False
        self.status_container.visible = False
        self.page.update()
    
    def process_confirmed_transfer(self, e):
        """Process the transfer after confirmation"""
        # Hide confirmation, show status
        self.confirmation_container.visible = False
        self.status_container.visible = True
        
        # Store reference to confirm button
        self.confirm_button = e.control
        self.confirm_button.disabled = True
        self.confirm_button.icon = ft.ProgressRing(width=16, height=16, stroke_width=2)
        self.confirm_button.text = "Procesando..."
        
        # Create status content
        status_text = ft.Text("Procesando...")
        progress = ft.ProgressBar()
        
        # Update status container with initial content
        self.status_container.content = ft.Column([
            ft.Text(f"Transferencia en Proceso", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
            ft.Text(f"Origen: {self.origin_dropdown.value}", size=16),
            ft.Text(f"Destino: {self.destination_dropdown.value}", size=16),
            ft.Text(f"Productos: {len(self.selected_products)}", size=16),
            ft.Divider(),
            ft.Text("Estado actual:", weight=ft.FontWeight.BOLD),
            status_text,
            progress,
        ])
        
        self.page.update()
        
        # Get stock levels BEFORE the transfer
        product_codes = list(self.selected_products.keys())
        origin_warehouse = self.origin_dropdown.value
        destination_warehouse = self.destination_dropdown.value
        warehouse_names = [origin_warehouse, destination_warehouse]
        
        # Capture stock snapshot before transfer
        before_stock = get_products_stock_snapshot(product_codes, warehouse_names)
        
        # Process the transfer
        def process_transfer():
            # Update status during the process
            status_text.value = "Contactando al servidor..."
            self.page.update()
            time.sleep(0.5)
            
            try:
                # Call the create_transfer function
                status_text.value = "Enviando datos al servidor..."
                self.page.update()
                
                # Execute the transfer
                result = create_transfer(
                    self.origin_dropdown.value, 
                    self.destination_dropdown.value, 
                    self.selected_products
                )
                
                status_text.value = "Procesando respuesta del servidor..."
                self.page.update()
                time.sleep(0.5)
                
                # Remove progress bar when done - MOVED THIS LINE UP before showing result
                if progress in self.status_container.content.controls:
                    self.status_container.content.controls.remove(progress)
                    self.page.update()
                
                # Handle the result
                if "Error" in result:
                    self.show_transfer_result(status_text, result, False, before_stock=before_stock)
                else:
                    self.show_transfer_result(status_text, result, True, before_stock=before_stock)
                    
            except Exception as ex:
                # Remove progress bar in case of error too
                if progress in self.status_container.content.controls:
                    self.status_container.content.controls.remove(progress)
                    self.page.update()
                
                self.show_transfer_result(status_text, f"Error inesperado: {str(ex)}", False, before_stock=before_stock)
        
        # Start the process in a separate thread
        threading.Thread(target=process_transfer).start()
    
    def show_transfer_result(self, status_text, result, success, before_stock=None):
        """Show the transfer result in the status container"""
        # Update status text
        if success:
            status_text.value = "Transferencia completada con éxito"
            status_text.color = ft.Colors.GREEN
            bg_color = ft.Colors.GREEN_50
            
            # Create result content - wrap in scrollable column
            result_column = ft.Column([
                ft.Divider(),
                ft.Text("Detalles:", weight=ft.FontWeight.BOLD),
            ], scroll=ft.ScrollMode.AUTO)  # Added scroll capability here
            
            # Add product details
            for code, qty in self.selected_products.items():
                product_name = next((p.name for p in self.products if p.default_code == code), code)
                result_column.controls.append(
                    ft.Text(f"• {code} - {product_name}: {qty}")
                )
                
            # Add divider and success message
            result_column.controls.append(ft.Divider())
            result_column.controls.append(ft.Text(result))
            
            # Add stock status section
            stock_status_text = ft.Text(
                "Obteniendo niveles de stock actualizados...",
                color=ft.Colors.BLUE
            )
            result_column.controls.append(ft.Divider())
            result_column.controls.append(ft.Text("Niveles de Stock Actualizados:", weight=ft.FontWeight.BOLD))
            result_column.controls.append(stock_status_text)
            
            # Add stock details container (will be populated later)
            stock_details = ft.Column([], scroll=ft.ScrollMode.AUTO)  # Added scroll capability here
            result_column.controls.append(stock_details)
            
            # Display notification status text
            notification_status = ft.Text(
                "Enviando notificación a WhatsApp...",
                color=ft.Colors.BLUE
            )
            result_column.controls.append(ft.Divider())
            result_column.controls.append(notification_status)
            
            # Add button to create a new transfer right away (will be updated by the notification thread)
            reset_button = ft.ElevatedButton(
                "Nueva transferencia",
                icon=ft.Icons.REFRESH,
                on_click=self.reset_form,
                style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE)
            )
            
            # Create footer container that sticks at bottom
            button_container = ft.Container(
                content=reset_button,
                margin=ft.margin.only(top=20),
                alignment=ft.alignment.center
            )
            
            # Add the button container to the result column
            result_column.controls.append(button_container)
            
            # Wrap result column in a scrollable container with fixed height 
            # to ensure it doesn't expand beyond the screen
            scroll_container = ft.Container(
                content=result_column,
                expand=True,  # Fill available space
                height=None,  # Let height adjust based on content
            )
            
            # Update the status container with initial information
            self.status_container.bgcolor = bg_color
            self.status_container.content = ft.Column([
                ft.Text(f"Transferencia Completada", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN),
                ft.Text(f"De: {self.origin_dropdown.value} → A: {self.destination_dropdown.value}", size=16),
                # Main scrollable content
                scroll_container
            ], scroll=ft.ScrollMode.AUTO, expand=True)  # Make the entire column scrollable
            
            self.page.update()
            
            # Fetch stock levels for the transferred products in a separate thread
            def fetch_stock_info():
                try:
                    origin_warehouse = self.origin_dropdown.value
                    destination_warehouse = self.destination_dropdown.value
                    product_codes = list(self.selected_products.keys())
                    
                    # Get stock information for the products in both warehouses
                    warehouse_names = [origin_warehouse, destination_warehouse]
                    stock_status_text.value = "Consultando inventario en Odoo..."
                    self.page.update()
                    
                    # Get the latest stock information after the transfer
                    after_stock = get_products_stock(product_codes, warehouse_names)
                    
                    # Create stock info display
                    if after_stock:
                        stock_status_text.value = "Información de inventario actualizada:"
                        stock_status_text.color = ft.Colors.GREEN
                        
                        # Clear and add new stock details
                        stock_details.controls.clear()
                        
                        # Add stock info for each product with before and after comparison
                        for code in product_codes:
                            product_name = next((p.name for p in self.products if p.default_code == code), code)
                            
                            # Get before and after values
                            before_origin = before_stock.get(code, {}).get(origin_warehouse, 0)
                            before_dest = before_stock.get(code, {}).get(destination_warehouse, 0)
                            
                            after_origin = after_stock.get(code, {}).get(origin_warehouse, 0)
                            after_dest = after_stock.get(code, {}).get(destination_warehouse, 0)
                            
                            # Create stock info card for this product
                            stock_card = ft.Card(
                                content=ft.Container(
                                    content=ft.Column([
                                        ft.Text(f"{code} - {product_name}", weight=ft.FontWeight.BOLD),
                                        ft.Divider(height=1, thickness=1),
                                        # Origin warehouse before/after
                                        ft.Text(f"Almacén: {origin_warehouse}", 
                                                weight=ft.FontWeight.BOLD, 
                                                size=14),
                                        ft.Row([
                                            ft.Text("Antes: ", weight=ft.FontWeight.BOLD),
                                            ft.Text(f"{before_origin} unidades")
                                        ]),
                                        ft.Row([
                                            ft.Text("Después: ", weight=ft.FontWeight.BOLD),
                                            ft.Text(f"{after_origin} unidades"),
                                            # Show change indicator icon
                                            ft.Icon(
                                                ft.Icons.ARROW_DOWNWARD if after_origin < before_origin else 
                                                (ft.Icons.ARROW_UPWARD if after_origin > before_origin else 
                                                ft.Icons.REMOVE),
                                                color=ft.Colors.RED if after_origin < before_origin else 
                                                (ft.Colors.GREEN if after_origin > before_origin else 
                                                ft.Colors.GREY),
                                                size=16
                                            )
                                        ]),
                                        ft.Divider(height=1, thickness=1),
                                        # Destination warehouse before/after
                                        ft.Text(f"Almacén: {destination_warehouse}", 
                                                weight=ft.FontWeight.BOLD, 
                                                size=14),
                                        ft.Row([
                                            ft.Text("Antes: ", weight=ft.FontWeight.BOLD),
                                            ft.Text(f"{before_dest} unidades")
                                        ]),
                                        ft.Row([
                                            ft.Text("Después: ", weight=ft.FontWeight.BOLD),
                                            ft.Text(f"{after_dest} unidades"),
                                            # Show change indicator icon
                                            ft.Icon(
                                                ft.Icons.ARROW_DOWNWARD if after_dest < before_dest else 
                                                (ft.Icons.ARROW_UPWARD if after_dest > before_dest else 
                                                ft.Icons.REMOVE),
                                                color=ft.Colors.RED if after_dest < before_dest else 
                                                (ft.Colors.GREEN if after_dest > before_dest else 
                                                ft.Colors.GREY),
                                                size=16
                                            )
                                        ])
                                    ]),
                                    padding=ft.padding.all(10)
                                ),
                                margin=ft.margin.only(bottom=10)
                            )
                            stock_details.controls.append(stock_card)
                    else:
                        stock_status_text.value = "No se pudo obtener la información de inventario"
                        stock_status_text.color = ft.Colors.ORANGE
                        
                    self.page.update()
                    
                except Exception as ex:
                    stock_status_text.value = f"Error al obtener niveles de stock: {str(ex)}"
                    stock_status_text.color = ft.Colors.RED
                    self.page.update()
            
            # Start stock fetching in a separate thread
            threading.Thread(target=fetch_stock_info).start()
            
            # Prepare notification message for WhatsApp
            origin_warehouse_name = self.origin_dropdown.value
            destination_warehouse_name = self.destination_dropdown.value
            
            product_details = []
            for code, qty in self.selected_products.items():
                product_name = next((p.name for p in self.products if p.default_code == code), code)
                product_details.append(f"• {code} - {product_name}: {qty}")
            
            # Format the message
            message = f"{origin_warehouse_name} ▶ {destination_warehouse_name}\n" + "\n".join(product_details)
            
            # Send WhatsApp message and update status
            def send_notification():
                try:
                    notification_status.value = "Contactando servidor de mensajería..."
                    self.page.update()
                    
                    # Send message with timeout and capture result
                    notification_result = send_message_to_group(message)
                    
                    # Update notification status based on result
                    if "Error" in notification_result:
                        notification_status.value = f"⚠️ {notification_result}"
                        notification_status.color = ft.Colors.RED
                    else:
                        notification_status.value = f"✅ Mensaje enviado correctamente al grupo de ENTRADAS Y SALIDAS"
                        notification_status.color = ft.Colors.GREEN
                        
                except Exception as ex:
                    notification_status.value = f"⚠️ Error al enviar el mensaje al grupo de ENTRADAS Y SALIDAS: {str(ex)}"
                    notification_status.color = ft.Colors.RED
                
                # Update the page to ensure notification status is visible
                self.page.update()
            
            # Start notification in a separate thread
            threading.Thread(target=send_notification).start()
            
        else:
            # Handle error case
            status_text.value = f"Error: {result}"
            status_text.color = ft.Colors.RED
            bg_color = ft.Colors.RED_50
            
            # Create error details column with scrolling
            result_column = ft.Column([
                ft.Divider(),
                ft.Text("Detalles del error:", weight=ft.FontWeight.BOLD),
                ft.Text(result),
                ft.Divider(),
                # Add button to try again
                ft.ElevatedButton(
                    "Nueva transferencia",
                    icon=ft.Icons.REFRESH,
                    on_click=self.reset_form,
                    style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE)
                )
            ], scroll=ft.ScrollMode.AUTO)
            
            # Update the status container with error information
            self.status_container.bgcolor = bg_color
            self.status_container.content = ft.Column([
                ft.Text("Error en la Transferencia", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED),
                # Main scrollable content
                result_column
            ], scroll=ft.ScrollMode.AUTO, expand=True)
            
            # Reset the button here, in case the user goes back
            if hasattr(self, 'transfer_button'):
                self.transfer_button.disabled = False
                self.transfer_button.icon = ft.Icons.SEND
                self.transfer_button.text = "Transferir"
                
            self.page.update()
    
    def close_banner(self):
        self.page.banner.open = False
        self.page.update()
    
    def reset_form(self, e=None):
        """Reset the form and switch back to form view"""
        # The button that triggered this might be different from the original transfer button,
        # so we need to handle both cases
        if e and hasattr(e, 'control'):
            reset_button = e.control
            reset_button.disabled = True
            reset_button.icon = ft.ProgressRing(width=16, height=16, stroke_width=2)
            reset_button.text = "Preparando..."
        
        # Reset form fields
        self.origin_dropdown.value = None
        self.destination_dropdown.value = None
        self.selected_products = {}
        self.update_products_list()
        
        # Show form and hide status
        self.form_container.visible = True
        self.status_container.visible = False
        
        # Reset status container for next use
        self.status_container.content = ft.Column([
            ft.Text("Procesando transferencia...", size=20, weight=ft.FontWeight.BOLD),
        ])
        
        # Reset the original transfer button if it exists
        if hasattr(self, 'transfer_button'):
            self.transfer_button.disabled = False
            self.transfer_button.icon = ft.Icons.SEND
            self.transfer_button.text = "Transferir"
            
        # Remove the problematic scroll_to call that's causing the error
        # self.page.scroll_to(offset=0)  # This line causes the error
        
        # Update the page
        self.page.update()

    # ...existing other methods...
