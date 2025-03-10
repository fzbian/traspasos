import flet as ft
from datetime import datetime
from utils import get_recent_transfers

class HistoryView(ft.View):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.route = "/history"
        self.appbar = ft.AppBar(
            title=ft.Text("Historial de Traspasos"),
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
        
        # Main progress indicator
        self.loading = ft.ProgressBar(width=400)
        
        # Status text for loading/errors
        self.status_text = ft.Text("Cargando transferencias desde Odoo...", color=ft.Colors.BLUE)
        
        # Create load button
        self.load_button = ft.ElevatedButton(
            "Cargar transferencias", 
            icon=ft.Icons.DOWNLOAD,
            on_click=self.load_transfers
        )
        
        # Details container that will appear below the list
        self.details_container = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Seleccione un traspaso para ver sus detalles", 
                            style=ft.TextStyle(italic=True))
                ]
            ),
            border=ft.border.all(1, ft.Colors.GREY_400),
            border_radius=10,
            padding=20,
            margin=ft.margin.only(top=20),
            visible=False
        )
        
        # Create the transfers list (using ListView instead of DataTable)
        self.transfers_list = ft.ListView(
            expand=True,
            spacing=10,
            padding=10
        )
        
        # Create a placeholder message to show until data is loaded
        self.placeholder = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Cargando historial de traspasos...", 
                           size=16, 
                           color=ft.Colors.GREY_800,
                           weight=ft.FontWeight.BOLD),
                    ft.Text("Consultando servidor de Odoo...",
                           color=ft.Colors.GREY)
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=5
            ),
            alignment=ft.alignment.center,
            expand=True
        )
        
        # Create the main content
        self.controls = [
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("Historial de Traspasos", size=20, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            controls=[
                                ft.ElevatedButton(
                                    "Nuevo",
                                    icon=ft.Icons.ADD,
                                    on_click=lambda e: self.page.go("/traspasos"),
                                    style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE, color=ft.Colors.WHITE)
                                ),
                                ft.OutlinedButton(
                                    "Actualizar",
                                    icon=ft.Icons.REFRESH,
                                    on_click=self.refresh_data
                                )
                            ],
                            alignment=ft.MainAxisAlignment.END,
                            wrap=True  # Allow wrapping on small screens
                        ),
                        self.status_text,
                        self.loading,
                        # Initial placeholder while loading
                        self.placeholder,
                        # Container for the actual data (initially hidden)
                        ft.Container(
                            content=self.transfers_list,
                            border=ft.border.all(1, ft.Colors.GREY_400),
                            border_radius=5,
                            padding=10,
                            expand=True,
                            visible=False  # Initially hidden until data is loaded
                        ),
                        # Add the details container below the list
                        self.details_container
                    ],
                    spacing=20
                ),
                padding=10,  # Reduced padding for mobile
                expand=True
            )
            # Loading overlay removed
        ]
        
        # Initialize traspasos list
        self.traspasos = []
        
        # Set the loading indicators to be visible by default
        self.loading.visible = True
        self.status_text.visible = True
        self.load_button.visible = False
        self._data_loaded = False
    
    def did_mount(self):
        """Called when the view is mounted/displayed"""
        # Start loading data
        self.load_transfers(None)
    
    def load_transfers(self, e=None):
        """Load transfer data from Odoo"""
        # Show loading state if triggered by a button
        triggering_button = None
        if e and hasattr(e, 'control'):
            triggering_button = e.control
            triggering_button.disabled = True
            if hasattr(triggering_button, 'icon'):
                triggering_button.icon = ft.ProgressRing(width=16, height=16, stroke_width=2)
            if hasattr(triggering_button, 'text'):
                triggering_button.text = "Cargando..."
            self.page.update()
        
        try:
            # Make sure loading indicators are visible
            self.loading.visible = True
            self.status_text.value = "Cargando transferencias desde Odoo..."
            self.status_text.visible = True
            self.load_button.visible = False
            self.placeholder.visible = True
            
            # Hide details container when loading new data
            self.details_container.visible = False
            self.page.update()
            
            # Synchronous loading - simpler but might freeze UI briefly
            self.traspasos = get_recent_transfers(10)
            
            # Update UI
            if not self.traspasos:
                self.status_text.value = "No se encontraron transferencias recientes"
                self.status_text.visible = True
                self.placeholder.visible = True
                self.controls[0].content.controls[5].visible = False
            else:
                self._update_transfers_list(self.traspasos)
                self.status_text.visible = False
                self.placeholder.visible = False
                self.controls[0].content.controls[5].visible = True
            
            # Hide loading indicators
            self.loading.visible = False
            self._data_loaded = True
            self.page.update()
            
            # Reset button if one was used
            if triggering_button:
                triggering_button.disabled = False
                if hasattr(triggering_button, 'icon'):
                    triggering_button.icon = ft.icons.REFRESH
                if hasattr(triggering_button, 'text'):
                    triggering_button.text = "Actualizar"
            
        except Exception as ex:
            # Show error
            self._show_error(f"Error al cargar datos: {str(ex)}")
            
            # Reset button if one was used
            if triggering_button:
                triggering_button.disabled = False
                if hasattr(triggering_button, 'icon'):
                    triggering_button.icon = ft.icons.REFRESH
                if hasattr(triggering_button, 'text'):
                    triggering_button.text = "Actualizar"
    
    def _update_transfers_list(self, transfers):
        """Update the transfers list with card-based UI for better mobile experience"""
        self.transfers_list.controls.clear()
        
        if not transfers:
            self.status_text.value = "No se encontraron transferencias recientes"
            self.status_text.visible = True
            self.placeholder.visible = True
            self.controls[0].content.controls[5].visible = False  # Hide the transfers list container
            return
            
        self.status_text.visible = False
        self.placeholder.visible = False
        self.controls[0].content.controls[5].visible = True  # Show the transfers list container
        
        for t in transfers:
            try:
                # Get transfer data
                traspaso_id = t.get('id', 'N/A')
                reference = t.get('reference', 'N/A')
                
                # Format the date for better readability
                date_str = t.get('date', 'N/A')
                try:
                    # Parse the date (which should already have AM/PM from utils.py)
                    if '%p' not in date_str:  # Only reformat if not already in AM/PM format
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        # Format it with AM/PM and day/month/year format
                        date = date_obj.strftime("%d/%m/%Y %I:%M:%S %p")
                    else:
                        # If already has AM/PM but needs dd/mm/yyyy format
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d %I:%M:%S %p")
                        date = date_obj.strftime("%d/%m/%Y %I:%M:%S %p")
                except:
                    date = date_str
                    
                origin = t.get('origin_warehouse', 'N/A')
                destination = t.get('destination_warehouse', 'N/A')
                products = t.get('products', {})
                state = t.get('state', 'done').capitalize()
                
                # Process product data for display
                product_text = "Sin productos"
                if products:
                    first_key = next(iter(products))
                    first_product = products[first_key]
                    product_name = first_product.get('name', 'Unknown')
                    product_text = f"{product_name}"
                    if len(products) > 1:
                        product_text += f" y {len(products) - 1} más"
                
                # Create a card for each transfer (better for mobile)
                card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(
                                    ft.Icons.SWAP_HORIZ, 
                                    color=ft.Colors.BLUE,
                                ),
                                title=ft.Text(
                                    f"{reference}",
                                    weight=ft.FontWeight.BOLD,
                                ),
                                subtitle=ft.Text(f"ID: {traspaso_id} | {date}"),
                            ),
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([
                                        ft.Icon(ft.Icons.ARROW_UPWARD, size=15, color=ft.Colors.GREEN),
                                        ft.Text(f"De: {origin}", size=14),
                                    ]),
                                    ft.Row([
                                        ft.Icon(ft.Icons.ARROW_DOWNWARD, size=15, color=ft.Colors.RED),
                                        ft.Text(f"A: {destination}", size=14),
                                    ]),
                                    ft.Row([
                                        ft.Icon(ft.Icons.INVENTORY_2, size=15),
                                        ft.Text(f"Prod: {product_text}", size=14),
                                    ]),
                                ], spacing=5),
                                padding=ft.padding.symmetric(horizontal=15)
                            ),
                            ft.Row([
                                ft.ElevatedButton(
                                    "Ver detalles",
                                    icon=ft.Icons.VISIBILITY,
                                    on_click=lambda e, id=traspaso_id: self.view_details(id),
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.Colors.BLUE,
                                        color=ft.Colors.WHITE
                                    )
                                )
                            ], alignment=ft.MainAxisAlignment.END)
                        ]),
                        padding=10
                    ),
                    elevation=2,
                    margin=10
                )
                
                # Add the card to the list
                self.transfers_list.controls.append(card)
                
            except Exception as ex:
                print(f"Error processing transfer: {ex}")
        
        # Show notification
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Se han cargado {len(transfers)} transferencias"),
            bgcolor=ft.Colors.GREEN
        )
        self.page.snack_bar.open = True

    def view_details(self, traspaso_id):
        """Show transfer details below the list"""
        # Add a small loading indicator on the page while loading details
        self.page.splash = ft.ProgressBar()
        self.page.update()
        
        # Find the transfer with matching ID
        traspaso = next((t for t in self.traspasos if t.get('id') == traspaso_id), None)
        
        if traspaso:
            try:
                # Get products data
                products = traspaso.get('products', {})
                
                # Create products list for display
                product_list = []
                for code, prod in products.items():
                    quantity = prod.get('quantity', 0)
                    planned = prod.get('planned_quantity', 0)
                    
                    product_info = f"• {code} - {prod.get('name', 'Unknown')}: {quantity}"
                    if planned != quantity and planned > 0:
                        product_info += f" (planificado: {planned})"
                        
                    product_list.append(product_info)
                
                # Format dates for better readability
                date_str = traspaso.get('date', 'N/A')
                scheduled_date_str = traspaso.get('scheduled_date', 'N/A')
                date_done_str = traspaso.get('date_done', 'N/A')
                
                try:
                    # Check if date already has AM/PM format
                    if '%p' not in date_str:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        formatted_date = date_obj.strftime("%d/%m/%Y %I:%M:%S %p")
                    else:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d %I:%M:%S %p")
                        formatted_date = date_obj.strftime("%d/%m/%Y %I:%M:%S %p")
                except:
                    formatted_date = date_str
                
                try:
                    if '%p' not in scheduled_date_str:
                        scheduled_date_obj = datetime.strptime(scheduled_date_str, "%Y-%m-%d %H:%M:%S")
                        formatted_scheduled_date = scheduled_date_obj.strftime("%d/%m/%Y %I:%M:%S %p")
                    else:
                        scheduled_date_obj = datetime.strptime(scheduled_date_str, "%Y-%m-%d %I:%M:%S %p")
                        formatted_scheduled_date = scheduled_date_obj.strftime("%d/%m/%Y %I:%M:%S %p")
                except:
                    formatted_scheduled_date = scheduled_date_str
                
                try:
                    if '%p' not in date_done_str:
                        date_done_obj = datetime.strptime(date_done_str, "%Y-%m-%d %H:%M:%S")
                        formatted_date_done = date_done_obj.strftime("%d/%m/%Y %I:%M:%S %p")
                    else:
                        date_done_obj = datetime.strptime(date_done_str, "%Y-%m-%d %I:%M:%S %p")
                        formatted_date_done = date_done_obj.strftime("%d/%m/%Y %I:%M:%S %p")
                except:
                    formatted_date_done = date_done_str
                
                # Create mobile-friendly details content
                details_content = ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.BLUE),
                        ft.Text("Detalles del Traspaso", 
                                size=16, 
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.BLUE),
                        ft.IconButton(
                            icon=ft.Icons.CLOSE,
                            tooltip="Cerrar detalles",
                            on_click=self.hide_details
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    
                    # Main content in a scrollable container
                    ft.Container(
                        content=ft.Column([
                            # Basic info section
                            ft.Text(f"Referencia: {traspaso.get('reference', 'N/A')}", 
                                    weight=ft.FontWeight.BOLD),
                            ft.Text(f"ID: {traspaso_id}"),
                            ft.Text(f"Origen: {traspaso.get('origin_location', traspaso.get('origin_warehouse', 'N/A'))}"),
                            ft.Text(f"Destino: {traspaso.get('destination_location', traspaso.get('destination_warehouse', 'N/A'))}"),
                            ft.Divider(),
                            
                            # Dates section
                            ft.Text("Fechas:", weight=ft.FontWeight.BOLD),
                            ft.Text(f"Creación: {formatted_date}"),
                            ft.Divider(),
                            
                            # Products section
                            ft.Text(f"Productos ({len(products)}):", weight=ft.FontWeight.BOLD),
                            ft.Container(
                                content=ft.Column([ft.Text(p) for p in product_list]),
                                margin=ft.margin.only(left=10)
                            )
                        ], scroll=ft.ScrollMode.AUTO),
                        height=300,
                    )
                ])
                
                # Update the details container
                self.details_container.content = details_content
                self.details_container.visible = True
                
                # Use a green background to highlight the selected transfer
                self.details_container.bgcolor = ft.Colors.GREEN_50
                
                self.page.update()
                
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Error al mostrar detalles: {str(ex)}"),
                    bgcolor=ft.Colors.RED
                )
                self.page.snack_bar.open = True
                self.page.update()
        
        self.page.splash = None  # Remove splash when done
    
    def hide_details(self, e=None):
        """Hide the details container"""
        self.details_container.visible = False
        self.page.update()
    
    def refresh_data(self, e):
        """Handle refresh button click"""
        # Show loading state
        refresh_button = e.control
        refresh_button.disabled = True
        refresh_button.icon = ft.ProgressRing(width=16, height=16, stroke_width=2)
        refresh_button.text = "Actualizando..."
        self.page.update()
        
        self._data_loaded = False
        self.hide_details()  # Hide details when refreshing
        
        # Pass the button to load_transfers so it can reset itself
        self.load_transfers(e)
    
    def _show_error(self, message):
        """Display error in UI"""
        print(f"Error in history view: {message}")
        
        # Hide loading indicators
        self.loading.visible = False
        self.placeholder.visible = False
        
        # Show error message
        self.status_text.value = message
        self.status_text.color = ft.Colors.RED
        self.status_text.visible = True
        self.load_button.visible = True
        
        # Show error in snackbar too
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.RED
        )
        self.page.snack_bar.open = True
        
        self.page.update()
