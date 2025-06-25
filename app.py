import gradio as gr
import requests
import pandas as pd

API_KEY = "giBN5pHlVloTPgljkdqgshcEEKjoC7WszomhMrAT" 

SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
DETAIL_URL = "https://api.nal.usda.gov/fdc/v1/food/{}"

# Almacenamiento temporal
alimentos_seleccionados = []

# Buscar alimentos por nombre
def buscar_alimentos(nombre_alimento):
    params = {
        "api_key": API_KEY,
        "query": nombre_alimento,
        "pageSize": 5,
        "dataType": ["Branded", "Foundation", "Survey (FNDDS)", "SR Legacy"]
    }
    response = requests.get(SEARCH_URL, params=params)
    data = response.json()
    resultados = []
    for item in data.get("foods", []):
        name = item.get("description", "Sin nombre")
        fdcId = item.get("fdcId")
        resultados.append(f"{name} (ID: {fdcId})")
    return resultados

# Obtener nutrientes por alimento y cantidad
def obtener_nutrientes(fdcId, gramos):
    url = DETAIL_URL.format(fdcId)
    response = requests.get(url, params={"api_key": API_KEY})
    data = response.json()

    nutrientes = {}
    for nutrient in data["foodNutrients"]:
        nombre = nutrient["nutrient"]["name"]
        unidad = nutrient["nutrient"]["unitName"]
        valor = nutrient.get("amount", 0)
        if valor is not None:
            nutrientes[nombre] = (valor, unidad)

    df = pd.DataFrame(nutrientes).T
    df.columns = ["Cantidad por 100g", "Unidad"]
    df["Total"] = df["Cantidad por 100g"] * (gramos / 100)
    return df[["Total", "Unidad"]]

# Añadir alimento a la lista
def agregar_alimento(seleccion, gramos):
    try:
        fdcId = int(seleccion.split("ID: ")[-1].replace(")", ""))
        nombre = seleccion.split(" (ID")[0]
        df_nutrientes = obtener_nutrientes(fdcId, gramos)
        df_nutrientes.rename(columns={"Total": nombre}, inplace=True)
        alimentos_seleccionados.append((nombre, gramos, df_nutrientes))
        return actualizar_tabla()
    except Exception as e:
        return f"Error: {e}"

# Eliminar todo
def limpiar():
    alimentos_seleccionados.clear()
    return pd.DataFrame()

# Combinar ingredientes
def actualizar_tabla():
    if not alimentos_seleccionados:
        return pd.DataFrame()

    total = alimentos_seleccionados[0][2].copy()
    for _, _, df in alimentos_seleccionados[1:]:
        total.update(total.iloc[:, :-1].add(df.iloc[:, :-1], fill_value=0))

    total["Unidad"] = alimentos_seleccionados[0][2]["Unidad"]
    total.reset_index(inplace=True)
    total.rename(columns={"index": "Nutriente"}, inplace=True)
    return total

with gr.Blocks() as demo:
    gr.Markdown("## Suma de Nutrientes de Varios Ingredientes de Alimentos (Datos de USDA)")
    with gr.Row():
        alimento_input = gr.Textbox(label="Buscar alimento en base de datos de USDA (en inglés)")
        resultados = gr.Dropdown(choices=[], label="Resultados")
        gramos_input = gr.Slider(10, 1000, step=10, value=100, label="Cantidad en gramos")
    with gr.Row():
        buscar_btn = gr.Button("Buscar alimento")
        agregar_btn = gr.Button("Agregar alimento")
        limpiar_btn = gr.Button("Limpiar todo")
    salida = gr.Dataframe(label="Tabla Nutricional Total")

    buscar_btn.click(fn=buscar_alimentos, inputs=alimento_input, outputs=resultados)
    agregar_btn.click(fn=agregar_alimento, inputs=[resultados, gramos_input], outputs=salida)
    limpiar_btn.click(fn=limpiar, outputs=salida)

demo.launch()

