from flask import Flask, request, jsonify, render_template_string
import pandas as pd
import requests
import os

app = Flask(__name__)

HTML_FORM = """
<!doctype html>
<title>Subir Excel</title>
<h2>Sube un archivo de facturas (.xlsx)</h2>
<form method=post enctype=multipart/form-data>
  <input type=file name=archivo>
  <input type=submit value=Enviar>
</form>
"""

@app.route('/', methods=['GET', 'POST'])
def subir_excel():
    if request.method == 'POST':
        archivo = request.files['archivo']
        if not archivo:
            return "No se seleccionó archivo", 400

        df = pd.read_excel(archivo)

        # Convertir a lista de diccionarios (JSON)
        lista_facturas = df.to_dict(orient='records')

        # Enviar al servidor Django
        try:
            respuesta = requests.post("http://127.0.0.1:8000/facturas/estado_resultados/", json=lista_facturas)
            return jsonify(respuesta.json())
        except Exception as e:
            return jsonify({'error': str(e)})

    return render_template_string(HTML_FORM)

if __name__ == '__main__':
    app.run(port=5002)
