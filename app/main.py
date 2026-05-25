from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware 
from .schema import InputData 
from .predict import predict_churn 
from .database import collection 
 
app = FastAPI() 
 
origins = ["*"]  # Para pruebas, luego limitar los origenes permitidos 
 
app.add_middleware( 
    CORSMiddleware, allow_origins=origins, allow_credentials=True, 
    allow_methods=["*"], allow_headers=["*"], 
) 
 
@app.post("/predict") 
def predict(data: InputData): 
    result = predict_churn(data) 
    return {"prediction": int(result)} 
 
@app.get("/stats") 
def stats(): 
    count = collection.count_documents({}) 
    churned = collection.count_documents({"prediction": 1}) 
    return {"total": count, "churned": churned} 