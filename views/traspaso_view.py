import flet as ft
from datetime import datetime
import threading
import time
from create_transfer import create_transfer
from utils import get_warehouses, get_products
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
        
        # Create the status container (initially hidden)
        self.status_container = ft.Container(
            content=ft.Column([
                ft.Text("Procesando transferencia...", size=20, weight=ft.FontWeight.BOLD),
            ]),
            padding=20,
            expand=True,
            visible=False
        )
        
        # Main container that will hold either form or status
        self.controls = [
            self.form_container,
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
            self.page.update()
            return
        
        try:    
            product_code = self.product_dropdown.value.split(" - ")[0]
            product_name = self.product_dropdown.value[len(product_code) + 3:]  # Skip " - "
            quantity = int(self.quantity_field.value)
            
            # Add to selected products
            self.selected_products[product_code] = quantity
            
            # Update products list
            self.update_products_list()
            
            # Reset product fields
            self.product_dropdown.value = None
            self.quantity_field.value = ""
            
            # Remove the keyboard dismiss code that's causing the error
            # Instead, we'll use this workaround to unfocus fields
            self.page.update()
            
            # Reset button state
            add_button.disabled = False
            add_button.icon = original_icon
            add_button.text = original_text
            self.page.update()
            
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Error al añadir producto: {str(ex)}"))
            self.page.snack_bar.open = True
            self.page.update()
            
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
        if product_code in self.selected_products:
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
            self.transfer_button.icon = ft.icons.SEND
            self.transfer_button.text = "Transferir"
            self.page.update()
            return
            
        if not self.destination_dropdown.value:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Por favor seleccione el destino"))
            self.page.snack_bar.open = True
            # Reset button
            self.transfer_button.disabled = False
            self.transfer_button.icon = ft.icons.SEND
            self.transfer_button.text = "Transferir"
            self.page.update()
            return
            
        if self.origin_dropdown.value == self.destination_dropdown.value:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("El origen y destino no pueden ser iguales"))
            self.page.snack_bar.open = True
            # Reset button
            self.transfer_button.disabled = False
            self.transfer_button.icon = ft.icons.SEND
            self.transfer_button.text = "Transferir"
            self.page.update()
            return
            
        if not self.selected_products:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Por favor añada al menos un producto"))
            self.page.snack_bar.open = True
            # Reset button
            self.transfer_button.disabled = False
            self.transfer_button.icon = ft.icons.SEND
            self.transfer_button.text = "Transferir"
            self.page.update()
            return
        
        # Hide form and show status
        self.form_container.visible = False
        self.status_container.visible = True
        
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
                
                # Handle the result
                if "Error" in result:
                    self.show_transfer_result(status_text, result, False)
                else:
                    self.show_transfer_result(status_text, result, True)
                    
            except Exception as ex:
                self.show_transfer_result(status_text, f"Error inesperado: {str(ex)}", False)
                
            # Remove progress bar when done
            self.status_container.content.controls.remove(progress)
            self.page.update()
        
        # Start the process in a separate thread
        threading.Thread(target=process_transfer).start()
    
    def show_transfer_result(self, status_text, result, success):
        """Show the transfer result in the status container"""
        # Update status text
        if success:
            status_text.value = "Transferencia completada con éxito"
            status_text.color = ft.Colors.GREEN
            bg_color = ft.Colors.GREEN_50
            
            # Create result content
            result_column = ft.Column([
                ft.Divider(),
                ft.Text("Detalles:", weight=ft.FontWeight.BOLD),
            ])
            
            # Add product details
            for code, qty in self.selected_products.items():
                product_name = next((p.name for p in self.products if p.default_code == code), code)
                result_column.controls.append(
                    ft.Text(f"• {code} - {product_name}: {qty}")
                )
                
            # Add divider and success message
            result_column.controls.append(ft.Divider())
            result_column.controls.append(ft.Text(result))
            
            # Display notification status text
            notification_status = ft.Text(
                "Enviando notificación a WhatsApp...",
                color=ft.Colors.BLUE
            )
            result_column.controls.append(ft.Divider())
            result_column.controls.append(notification_status)
            
            # Update the status container with initial information
            self.status_container.bgcolor = bg_color
            self.status_container.content.controls.extend(result_column.controls)
            self.page.update()
            
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
                
                # Add button to create a new transfer after notification handling
                self.status_container.content.controls.append(
                    ft.ElevatedButton(
                        "Nueva transferencia",
                        icon=ft.Icons.REFRESH,
                        on_click=self.reset_form,
                        style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE)
                    )
                )
                self.page.update()
            
            # Start notification in a separate thread
            threading.Thread(target=send_notification).start()
            
        else:
            # Handle error case
            status_text.value = f"Error: {result}"
            status_text.color = ft.Colors.RED
            bg_color = ft.Colors.RED_50
            
            # Create error details column
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
            ])
            
            # Update the status container with error information
            self.status_container.bgcolor = bg_color
            self.status_container.content.controls.extend(result_column.controls)
            
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
            
        # Update the page
        self.page.update()
    
    # ...existing other methods...
