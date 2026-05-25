import joblib 
import datetime 
import pandas as pd 
from .database import collection 
 
model = joblib.load("model/churn_model.pkl") 
 
def predict_churn(data): 
    features = [[data.tenure, data.monthlycharges, data.contract]] 
 
    # Crear un DataFrame con los nombres para prediccion 
    input_df = pd.DataFrame([{ 
        "tenure": data.tenure, 
        "MonthlyCharges": data.monthlycharges, 
        "Contract": data.contract 
    }]) 
 
    prediction = model.predict(input_df)[0] 
    collection.insert_one({ 
        "input": data.dict(), 
        "prediction": int(prediction), 
        "timestamp": datetime.datetime.utcnow() 
    }) 
    return prediction 