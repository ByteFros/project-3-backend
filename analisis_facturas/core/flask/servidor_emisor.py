# servidor_emisor.py
from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/enviar_factura', methods=['GET'])
def enviar_factura():
    factura = {
        'id_unico': 'EXT-001',
        'numero': 'EXT-A001',
        'cliente': 'Cliente Remoto',
        'fecha': '2025-05-22',
        'subtotal': 450.00
    }

    try:
        respuesta = requests.post("http://127.0.0.1:8000/facturas/factura_json/", json=factura)
        return jsonify(respuesta.json())
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(port=5001)
