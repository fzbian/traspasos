import flet as ft
from datetime import datetime
from utils import get_recent_transfers, get_warehouses
import threading
import time

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
        
        # Get warehouse data for filtering
        self.warehouses = get_warehouses()
        
        # Set default limit for transfers to display
        self.transfer_limit = 15
        
        # Create filter controls
        self.warehouse_filter = ft.Dropdown(
            label="Filtrar por almacén",
            hint_text="Todos los almacenes",
            options=[
                ft.dropdown.Option("Todos"),
                *[ft.dropdown.Option(warehouse.name) for warehouse in self.warehouses]
            ],
            width=250,
        )
        
        self.limit_selector = ft.Dropdown(
            label="Cantidad a mostrar",
            value=str(self.transfer_limit),
            options=[
                ft.dropdown.Option("5"),
                ft.dropdown.Option("10"),
                ft.dropdown.Option("15"),
                ft.dropdown.Option("20"),
                ft.dropdown.Option("50"),
                ft.dropdown.Option("100"),
            ],
            width=120,
        )
        
        # Apply filters button
        self.apply_filters_button = ft.ElevatedButton(
            "Aplicar filtros",
            icon=ft.Icons.FILTER_LIST,
            on_click=self.apply_filters,
            style=ft.ButtonStyle(color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE)
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
        
        # Add a dictionary to store the original cards
        self.original_cards = {}
        
        # Create the transfers list (using ListView instead of DataTable)
        self.transfers_list = ft.ListView(
            expand=True,
            spacing=10,
            padding=10,
            auto_scroll=True
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
        
        # Create filters container
        self.filters_container = ft.Container(
            content=ft.Column([
                ft.Text("Opciones de filtrado", size=16, weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow([
                    ft.Column([self.warehouse_filter], col={"xs": 12, "sm": 5}),
                    ft.Column([self.limit_selector], col={"xs": 6, "sm": 3}),
                    ft.Column([self.apply_filters_button], col={"xs": 6, "sm": 4}, horizontal_alignment=ft.CrossAxisAlignment.END)
                ])
            ]),
            border=ft.border.all(1, ft.Colors.GREY_400),
            border_radius=5,
            padding=10,
            margin=ft.margin.only(bottom=15)
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
                        # Add filters container
                        self.filters_container,
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
                    ],
                    spacing=15,
                    scroll=ft.ScrollMode.AUTO,  # Enable scrolling for the whole view
                    expand=True  # Allow column to expand to fill available space
                ),
                padding=10,  # Reduced padding for mobile
                expand=True
            )
        ]
        
        # Initialize traspasos list
        self.traspasos = []
        self.filtered_traspasos = []
        self.selected_warehouse = None
        
        # Set the loading indicators to be visible by default
        self.loading.visible = True
        self.status_text.visible = True
        self.load_button.visible = False
        self._data_loaded = False
    
    def did_mount(self):
        """Called when the view is mounted/displayed"""
        # Start loading data
        self.load_transfers(None)
    
    def apply_filters(self, e=None):
        """Apply selected filters to the transfers list"""
        # Show loading state on the button
        if e and hasattr(e, 'control'):
            filter_button = e.control
            filter_button.disabled = True
            filter_button.icon = ft.ProgressRing(width=16, height=16, stroke_width=2)
            filter_button.text = "Aplicando..."
            self.page.update()
        
        # Get selected limit
        try:
            self.transfer_limit = int(self.limit_selector.value)
        except (ValueError, TypeError):
            self.transfer_limit = 15  # Default to 15 if invalid
        
        # Get selected warehouse
        selected_warehouse = self.warehouse_filter.value
        if selected_warehouse == "Todos" or not selected_warehouse:
            self.selected_warehouse = None
        else:
            self.selected_warehouse = selected_warehouse
        
        # Always reload data when filters change - server-side filtering is more efficient
        self._data_loaded = False
        self.load_transfers(e)
    
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
            self.page.update()
            
            # Get the limit value from the selector
            try:
                limit = int(self.limit_selector.value)
            except (ValueError, TypeError):
                limit = 15  # Default to 15 if invalid
                
            # Get selected warehouse filter
            selected_warehouse = self.warehouse_filter.value
            if (selected_warehouse == "Todos" or not selected_warehouse):
                selected_warehouse = None
            
            # Store warehouse selection for consistent behavior
            self.selected_warehouse = selected_warehouse
            
            # Store references to components that need to be updated
            status_text_ref = self.status_text
            placeholder_ref = self.placeholder
            controls_ref = self.controls[0].content.controls[6]
            loading_ref = self.loading
            
            # Store button reference if triggered by button click
            triggering_button_ref = None
            if e and hasattr(e, 'control'):
                triggering_button_ref = e.control
            
            # Load data in a separate thread to keep UI responsive
            def load_data_thread():
                # Fetch data from Odoo with the specified limit and warehouse filter
                fetched_data = get_recent_transfers(limit, selected_warehouse)
                
                # Store unfiltered data for future reference
                self.traspasos = fetched_data
                self.filtered_traspasos = fetched_data  # No client-side filtering needed anymore
                self._data_loaded = True
                
                # Call a method to update UI in the main thread
                self._schedule_ui_update(
                    fetched_data, 
                    status_text_ref, 
                    placeholder_ref, 
                    controls_ref, 
                    loading_ref,
                    triggering_button_ref
                )
            
            # Start loading process in background
            threading.Thread(target=load_data_thread).start()
            
        except Exception as ex:
            # Show error
            self._show_error(f"Error al cargar datos: {str(ex)}")
            
            # Reset button if one was used
            if triggering_button:
                triggering_button.disabled = False
                if hasattr(triggering_button, 'icon'):
                    triggering_button.icon = ft.Icons.REFRESH
                if hasattr(triggering_button, 'text'):
                    triggering_button.text = "Actualizar"
    
    def _schedule_ui_update(self, filtered_data, status_text, placeholder, controls, loading, button=None):
        """Schedule UI update on the main thread"""
        # We'll use a simple time-based approach with a minimal delay
        time.sleep(0.1)  # Brief delay to ensure thread synchronization
        
        # This code will run in the original thread, so it's safe to update UI
        def update_ui_callback():
            try:
                # Update UI based on filtered data
                if not filtered_data:
                    status_text.value = "No se encontraron transferencias"
                    status_text.visible = True
                    placeholder.visible = True
                    controls.visible = False
                else:
                    self._update_transfers_list(filtered_data)
                    status_text.visible = False
                    placeholder.visible = False
                    controls.visible = True
                
                # Hide loading indicators
                loading.visible = False
                
                # Reset button if one was used
                if button:
                    button.disabled = False
                    if hasattr(button, 'icon'):
                        button.icon = ft.Icons.REFRESH
                    if hasattr(button, 'text'):
                        button.text = "Actualizar"
                
                self.page.update()
                
                # Show notification about loaded transfers
                if filtered_data:
                    self.page.snack_bar = ft.SnackBar(
                        content=ft.Text(f"Se han cargado {len(filtered_data)} transferencias"),
                        bgcolor=ft.Colors.GREEN
                    )
                    self.page.snack_bar.open = True
                    self.page.update()
            except Exception as ex:
                print(f"Error updating UI: {ex}")
        
        # Execute the update
        update_ui_callback()
    
    def _update_transfers_list(self, transfers):
        """Update the transfers list with card-based UI for better mobile experience"""
        self.transfers_list.controls.clear()
        self.original_cards = {}  # Reset the saved original cards
        
        if not transfers:
            self.status_text.value = "No se encontraron transferencias recientes"
            self.status_text.visible = True
            self.placeholder.visible = True
            self.controls[0].content.controls[6].visible = False  # Hide the transfers list container
            return
            
        self.status_text.visible = False
        self.placeholder.visible = False
        self.controls[0].content.controls[6].visible = True  # Show the transfers list container
        
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
                                    on_click=lambda e, id=traspaso_id, idx=len(self.transfers_list.controls): 
                                        self.view_details(id, idx),
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
                    margin=10,
                    data=traspaso_id  # Store the ID in the card's data for reference
                )
                
                # Store the card in the dictionary, using its index as the key
                self.original_cards[len(self.transfers_list.controls)] = card
                
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

    def view_details(self, traspaso_id, card_index):
        """Replace the card with transfer details"""
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
                
                # Create details card that will replace the original card
                details_card = ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.BLUE),
                                ft.Text("Detalles del Traspaso", 
                                        size=16, 
                                        weight=ft.FontWeight.BOLD,
                                        color=ft.Colors.BLUE,
                                        expand=True),
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    tooltip="Cerrar detalles",
                                    on_click=lambda e, idx=card_index: self.hide_details(idx)
                                )
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Divider(),
                            
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
                            # Make the product list scrollable with a fixed height
                            ft.Container(
                                content=ft.ListView(
                                    controls=[ft.Text(p) for p in product_list],
                                    spacing=5
                                ),
                                height=150,
                                border=ft.border.all(1, ft.Colors.GREY_300),
                                border_radius=5,
                                padding=10
                            )
                        ], scroll=ft.ScrollMode.AUTO),
                        padding=15
                    ),
                    elevation=4,
                    margin=10,
                    color=ft.Colors.BLUE_GREY_50
                )
                
                # Replace the card in the list with the details card
                if 0 <= card_index < len(self.transfers_list.controls):
                    self.transfers_list.controls[card_index] = details_card
                    self.page.update()
                
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Error al mostrar detalles: {str(ex)}"),
                    bgcolor=ft.Colors.RED
                )
                self.page.snack_bar.open = True
                self.page.update()
        
        self.page.splash = None  # Remove splash when done
    
    def hide_details(self, card_index=None):
        """Restore the original card view"""
        # If no card index is provided, no action needed
        if card_index is None:
            return
            
        # Check if we have the original card saved
        if card_index in self.original_cards:
            # Restore the original card
            self.transfers_list.controls[card_index] = self.original_cards[card_index]
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
        self.hide_details()  # Hide details when refreshing - now works without argument
        
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
