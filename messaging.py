import requests

def send_message_to_group(message):
    url = 'http://137.184.137.192:3000/send-message-group'
    payload = {
        'group_name': "ENTRADAS Y SALIDAS",
        'message': message
    }
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        return "Message sent successfully."
    else:
        return f"Failed to send message. Status code: {response.status_code}"
