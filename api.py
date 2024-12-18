import os
from dotenv import load_dotenv
from fastapi import FastAPI 
from tensorflow.keras.models import load_model
import joblib
import numpy as np
from tensorflow.keras.preprocessing.image import img_to_array, load_img
import json  
import requests  
from pydantic import BaseModel
from fastapi import HTTPException
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Cargar variables de entorno
load_dotenv()

# Cargar rutas desde variables de entorno
base_model_path = os.getenv("BASE_MODEL_PATH")
svm_model_path = os.getenv("SVM_MODEL_PATH")
id_names_path = os.getenv("ID_NAMES_PATH") 

# Cargar modelos y clases al inicio
base_model = load_model(base_model_path)
svm_model = joblib.load(svm_model_path)

with open(id_names_path, "r") as f:
    id_names = json.load(f)

class_name = list(id_names.keys())  
 

def download_image_from_url(url, img_path):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Lanza una excepción si el estado de la respuesta no es 200
        with open(img_path, "wb") as img_file:
            img_file.write(response.content)
    except requests.exceptions.RequestException as e:
        # Captura cualquier error relacionado con la solicitud HTTP
        raise HTTPException(400, detail=f"Error al descargar la imagen: {str(e)}")

 
# Función de predicción   
def predict_image(img_path):
    try:
        img = load_img(img_path, target_size=(224, 224))
        img_array = img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
    
        # Extraer características con MobileNetV2
        features = base_model.predict(img_array)
        features_flat = features.reshape((features.shape[0], -1))

        # Clasificar usando SVM
        prediction = svm_model.predict(features_flat)
        predicted_class = class_name[prediction[0]]
        
        # Obtener la ID desde ID_names
        if predicted_class in id_names:
            predicted_id = id_names[predicted_class]
            return {"id": predicted_id, "classname": predicted_class}  # Devuelve ambos valores
        else:
            raise ValueError(f"No se encontró información para la plaga: {predicted_class}")
     
    except Exception as e:
        raise HTTPException(500, detail=f"Error en la predicción de la imagen: {str(e)}")


class ImageRequest(BaseModel):
    image_url: str


# Configurar CORS para permitir solicitudes desde localhost:8100
origins = [
    "http://localhost:8100",  # Dirección de tu aplicación Ionic
    "http://127.0.0.1:8100",  # Dirección alternativa para localhost
]

# Agregar middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los encabezados
)
 

# Endpoint para recibir imagen y devolver predicción
@app.post("/prediccion/")
async def predict(image_request: ImageRequest):
    try:
        image_url = image_request.image_url
        # Definir el nombre de archivo temporal para la imagen
        img_path = "temp_image.jpg"
        
        # Descargar la imagen desde Firebase Storage
        download_image_from_url(image_url, img_path)

        # Realizar predicción
        resultado_prediccion = predict_image(img_path)

        # Retornar solo el nombre de la plaga detectada
        return resultado_prediccion 

    except HTTPException as e:
        # Maneja excepciones HTTP relacionadas con la descarga o la predicción
        raise e
    except Exception as e:
        # Captura cualquier otro error inesperado
        raise HTTPException(500, detail=f"Error inesperado: {str(e)}")