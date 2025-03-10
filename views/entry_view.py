import flet as ft
from datetime import datetime
import threading
import time
from create_entry import create_entry
from utils import get_warehouses, get_products
from config import Producto  # Import the Producto class

class EntryView(ft.View):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.route = "/entries"
        self.appbar = ft.AppBar(
            title=ft.Text("Crear Nueva Entrada"),
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
        
        # Selected products for entry - now a list of Producto objects
        self.selected_products = []  # List of Producto objects
        
        # Form fields - all responsive for mobile
        self.warehouse_dropdown = ft.Dropdown(
            label="Almacén Destino",
            options=[
                ft.dropdown.Option(warehouse.name) for warehouse in self.warehouses
            ],
            expand=True,  # Fill available width
            autofocus=True
        )
        
        # Product selection fields - responsive for mobile
        self.product_dropdown = ft.Dropdown(
            label="Producto",
            expand=True,
            options=[
                ft.dropdown.Option(f"{p.default_code} - {p.name}") for p in self.products if p.default_code
            ],
            hint_text="Seleccione un producto"
        )
        
        self.quantity_field = ft.TextField(
            label="Cantidad",
            width=100,
            hint_text="Cantidad",
        )
        
        self.cost_field = ft.TextField(
            label="Costo Unitario",
            width=100,
            hint_text="Costo",
        )
        
        # Products list - scrollable and responsive
        self.products_list = ft.ListView(
            expand=True,
            spacing=10,
            padding=10,
            auto_scroll=True,
            height=200
        )
        
        # Create the form container (all form elements)
        self.form_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Complete el formulario de entrada", size=20, weight=ft.FontWeight.BOLD),
                    
                    # Warehouse section - removed origin field
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Información de Entrada:", size=16, weight=ft.FontWeight.BOLD),
                            self.warehouse_dropdown,
                        ]),
                        margin=ft.margin.only(bottom=10)
                    ),
                    
                    # Products selection section
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Añadir productos:", size=16, weight=ft.FontWeight.BOLD),
                            # Responsive product selection row
                            ft.ResponsiveRow(
                                controls=[
                                    ft.Column([self.product_dropdown], col={"xs": 12, "sm": 6}),
                                    ft.Column([self.quantity_field], col={"xs": 6, "sm": 2}),
                                    ft.Column([self.cost_field], col={"xs": 6, "sm": 2}),
                                    ft.Column([
                                        ft.ElevatedButton(
                                            "Añadir",
                                            icon=ft.Icons.ADD,
                                            on_click=self.add_product,
                                            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE)
                                        )
                                    ], col={"xs": 12, "sm": 2})
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
                    
                    # Action buttons - for touch on mobile
                    ft.ResponsiveRow(
                        controls=[
                            ft.Column([
                                ft.ElevatedButton(
                                    "Procesar Entrada",
                                    icon=ft.Icons.SAVE,
                                    on_click=self.save_entry,
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
                ft.Text("Procesando entrada...", size=20, weight=ft.FontWeight.BOLD),
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
        # Show loading state on the button that triggered the event
        original_button = e.control
        original_icon = original_button.icon
        original_text = original_button.text
        
        original_button.disabled = True
        original_button.icon = ft.ProgressRing(width=16, height=16, stroke_width=2)
        original_button.text = "Añadiendo..."
        self.page.update()
        
        # Validate product selection
        if not self.product_dropdown.value:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Por favor seleccione un producto"))
            self.page.snack_bar.open = True
            # Reset button
            original_button.disabled = False
            original_button.icon = original_icon
            original_button.text = original_text
            self.page.update()
            return
            
        # Validate quantity
        if not self.quantity_field.value or not self.quantity_field.value.isdigit() or int(self.quantity_field.value) <= 0:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Por favor ingrese una cantidad válida"))
            self.page.snack_bar.open = True
            # Reset button
            original_button.disabled = False
            original_button.icon = original_icon
            original_button.text = original_text
            self.page.update()
            return
        
        # Validate cost
        try:
            cost = float(self.cost_field.value.replace(',', '.'))
            if cost <= 0:
                raise ValueError("El costo debe ser mayor a cero")
        except ValueError:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Por favor ingrese un costo válido"))
            self.page.snack_bar.open = True
            # Reset button
            original_button.disabled = False
            original_button.icon = original_icon
            original_button.text = original_text
            self.page.update()
            return
        
        try:    
            product_code = self.product_dropdown.value.split(" - ")[0]
            product_name = self.product_dropdown.value[len(product_code) + 3:]  # Skip " - "
            quantity = int(self.quantity_field.value)
            
            # Create a Producto object and add it to the list
            producto = Producto(product_code, quantity, cost)
            
            # Check if product already exists in the list
            existing_idx = None
            for idx, p in enumerate(self.selected_products):
                if p.referencia == product_code:
                    existing_idx = idx
                    break
                    
            if existing_idx is not None:
                # Update existing product
                self.selected_products[existing_idx] = producto
            else:
                # Add new product
                self.selected_products.append(producto)
            
            # Update products list
            self.update_products_list()
            
            # Reset product fields
            self.product_dropdown.value = None
            self.quantity_field.value = ""
            self.cost_field.value = ""
            
            # Reset button
            original_button.disabled = False
            original_button.icon = original_icon
            original_button.text = original_text
            self.page.update()
        except Exception as ex:
            self.page.snack_bar = ft.SnackBar(content=ft.Text(f"Error al añadir producto: {str(ex)}"))
            self.page.snack_bar.open = True
            # Reset button
            original_button.disabled = False
            original_button.icon = original_icon
            original_button.text = original_text
            self.page.update()
    
    def update_products_list(self):
        # Clear existing list
        self.products_list.controls.clear()
        
        # Add each product to the list with responsive layout
        for producto in self.selected_products:
            # Find product name from reference code
            product_name = next((p.name for p in self.products if p.default_code == producto.referencia), producto.referencia)
            
            # Create a delete button with a fixed product code reference
            delete_button = ft.IconButton(
                icon=ft.Icons.DELETE,
                tooltip="Eliminar",
                data=producto.referencia,  # Store the reference code as data
                icon_size=24  # Bigger icon for touch
            )
            delete_button.on_click = self.create_delete_handler(producto.referencia)
            
            # Create touch-friendly rows
            self.products_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Text(
                                    f"{producto.referencia} - {product_name}", 
                                    expand=True,
                                    weight=ft.FontWeight.BOLD,
                                    size=14
                                ),
                                delete_button
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Row([
                                ft.Text(
                                    f"Cantidad: {producto.cantidad}",
                                    expand=True,
                                    size=12
                                ),
                                ft.Text(
                                    f"Costo: ${producto.costo:.2f}",
                                    size=12
                                ),
                            ])
                        ]),
                        padding=10  # Add padding inside the card
                    ),
                    margin=ft.margin.only(bottom=5)
                )
            )
        
        self.page.update()
    
    def create_delete_handler(self, reference):
        """Create a dedicated handler function for each delete button"""
        def handle_delete(e):
            self.remove_product(reference)
        return handle_delete
    
    def remove_product(self, reference):
        # Find and remove the product with the matching reference
        self.selected_products = [p for p in self.selected_products if p.referencia != reference]
        self.update_products_list()
    
    def save_entry(self, e):
        # Show loading state on the button
        original_button = e.control
        original_button.disabled = True
        original_button.icon = ft.ProgressRing(width=16, height=16, stroke_width=2)
        original_button.text = "Procesando..."
        self.page.update()
        
        # Validate inputs
        if not self.warehouse_dropdown.value:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Por favor seleccione el almacén destino"))
            self.page.snack_bar.open = True
            # Reset button
            original_button.disabled = False
            original_button.icon = ft.icons.SAVE
            original_button.text = "Procesar Entrada"
            self.page.update()
            return
        
        if not self.selected_products:
            self.page.snack_bar = ft.SnackBar(content=ft.Text("Por favor añada al menos un producto"))
            self.page.snack_bar.open = True
            # Reset button
            original_button.disabled = False
            original_button.icon = ft.icons.SAVE
            original_button.text = "Procesar Entrada"
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
            ft.Text(f"Entrada en Proceso", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE),
            ft.Text(f"Almacén Destino: {self.warehouse_dropdown.value}", size=16),
            ft.Text(f"Productos: {len(self.selected_products)}", size=16),
            ft.Divider(),
            ft.Text("Estado actual:", weight=ft.FontWeight.BOLD),
            status_text,
            progress,
        ])
        
        self.page.update()
        
        # Process the entry
        def process_entry():
            # Update status during the process
            status_text.value = "Contactando al servidor..."
            self.page.update()
            time.sleep(0.5)
            
            try:
                # Call the create_entry function with the correct parameters
                status_text.value = "Enviando datos al servidor..."
                self.page.update()
                
                # Execute the entry creation with the correct parameters
                result = create_entry(
                    self.warehouse_dropdown.value,
                    self.selected_products
                )
                
                status_text.value = "Procesando respuesta del servidor..."
                self.page.update()
                time.sleep(0.5)
                
                # Handle the result
                if isinstance(result, str) and "Error" in result:
                    self.show_entry_result(status_text, result, False)
                else:
                    self.show_entry_result(status_text, str(result), True)
                    
            except Exception as ex:
                self.show_entry_result(status_text, f"Error inesperado: {str(ex)}", False)
                
            # Remove progress bar when done
            self.status_container.content.controls.remove(progress)
            self.page.update()
        
        # Start the process in a separate thread
        threading.Thread(target=process_entry).start()
    
    def show_entry_result(self, status_text, result, success):
        """Show the entry result in the status container"""
        # Update status text
        if success:
            status_text.value = "Entrada completada con éxito"
            status_text.color = ft.Colors.GREEN
            bg_color = ft.Colors.GREEN_50
        else:
            status_text.value = f"Error: {result}"
            status_text.color = ft.Colors.RED
            bg_color = ft.Colors.RED_50
        
        # Create result content
        result_column = ft.Column([
            ft.Divider(),
            ft.Text("Detalles de Productos:", weight=ft.FontWeight.BOLD),
        ])
        
        # Add product details if successful
        if success:
            for producto in self.selected_products:
                product_name = next((p.name for p in self.products if p.default_code == producto.referencia), producto.referencia)
                result_column.controls.append(
                    ft.Text(f"• {producto.referencia} - {product_name}: {producto.cantidad} unidades a ${producto.costo:.2f}")
                )
            result_column.controls.append(ft.Divider())
            result_column.controls.append(ft.Text(result))
        
        # Add button to create a new entry
        result_column.controls.append(
            ft.ElevatedButton(
                "Nueva entrada",
                icon=ft.Icons.REFRESH,
                on_click=self.reset_form,
                style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE)
            )
        )
        
        # Update the status container
        self.status_container.bgcolor = bg_color
        self.status_container.content.controls.extend(result_column.controls)
        self.page.update()
    
    def reset_form(self, e=None):
        # Show loading state if this was triggered by a button
        if e and hasattr(e, 'control'):
            original_button = e.control
            original_button.disabled = True
            original_button.icon = ft.ProgressRing(width=16, height=16, stroke_width=2)
            original_button.text = "Preparando..."
            self.page.update()
        
        # Reset form fields
        self.warehouse_dropdown.value = None
        self.selected_products = []
        self.update_products_list()
        
        # Show form and hide status
        self.form_container.visible = True
        self.status_container.visible = False
        
        # Reset status container for next use
        self.status_container.content = ft.Column([
            ft.Text("Procesando entrada...", size=20, weight=ft.FontWeight.BOLD),
        ])
        
        self.page.update()
