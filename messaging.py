import requests
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from requests.exceptions import RequestException

def send_message_to_group(message, group_name="A", timeout=60):
    """
    Send a message to a specific group with timeout and error handling
    
    Args:
        message (str): The message to send
        group_name (str): Target group name (default: "A")
        timeout (int): Maximum time to wait for response in seconds (default: 60)
        
    Returns:
        str: Message indicating success or failure
    """
    url = 'http://137.184.137.192:3000/send-message-group'
    payload = {
        'group_name': group_name,
        'message': message
    }
    
    # Function to execute the request in a separate thread
    def execute_request():
        try:
            # Send the request with a timeout
            response = requests.post(url, json=payload, timeout=timeout)
            
            # Process response
            if response.status_code == 200:
                # Try to parse JSON response if available
                try:
                    resp_data = response.json()
                    if isinstance(resp_data, dict) and 'message' in resp_data:
                        return f"Mensaje enviado: {resp_data['message']}"
                except:
                    # If JSON parsing fails, return simple success
                    return "Mensaje enviado correctamente."
                
                return "Mensaje enviado correctamente."
            else:
                # Format error based on status code
                return f"Error al enviar mensaje. Respuesta del servidor: [{response.status_code}] {response.text}"
                
        except requests.Timeout:
            return "Error: Tiempo de espera agotado. El servidor tardó demasiado en responder."
        except RequestException as e:
            return f"Error de conexión: {str(e)}"
        except Exception as e:
            return f"Error inesperado: {str(e)}"
    
    # Use ThreadPoolExecutor to handle timeout
    with ThreadPoolExecutor(max_workers=1) as executor:
        try:
            # Start the request in a separate thread and wait for result with timeout
            future = executor.submit(execute_request)
            result = future.result(timeout=timeout)
            return result
        except TimeoutError:
            # Handle timeout case
            return "Error: No se pudo enviar el mensaje. El tiempo de espera (1 minuto) ha transcurrido."
        except Exception as e:
            # Handle any other exception
            return f"Error al enviar mensaje: {str(e)}"