from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
import numpy as np
import cv2
from keras.models import load_model  # type: ignore

app = FastAPI()

# Load your trained model
model = load_model("vehicle_classifier_ZAM_main.h5")


class PredictionResult(BaseModel):
    label: str
    confidence: float


def preprocess_image(image: np.ndarray, size: tuple = (224, 224)) -> np.ndarray:
    image = cv2.resize(image, size)
    image = image.astype("float32") / 255.0
    return np.expand_dims(image, axis=0)


def predict(image: np.ndarray) -> PredictionResult:
    prediction = model.predict(image)
    class_idx = np.argmax(prediction)
    confidence = float(np.max(prediction))
    label = ["bike", "buses", "car", "truck"][class_idx]
    return PredictionResult(label=label, confidence=confidence)


@app.post("/predict/", response_model=PredictionResult)
async def predict_vehicle(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    processed_image = preprocess_image(image)
    result = predict(processed_image)
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
