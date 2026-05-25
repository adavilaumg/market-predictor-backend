import pandas as pd 
from sklearn.model_selection import train_test_split 
from sklearn.ensemble import RandomForestClassifier 
from sklearn.linear_model import LogisticRegression 
import joblib 
 
# 1. Cargar dataset de Kaggle 
df = pd.read_csv("model-mockup.csv") 
 
# 2. Preprocesar (versión simple) 
df = df[["tenure", "MonthlyCharges", "Contract", "Churn"]] 
df["Contract"] = df["Contract"].astype("category").cat.codes 
df["Churn"] = df["Churn"].map({"Yes": 1, "No": 0}) 
 
X = df[["tenure", "MonthlyCharges", "Contract"]] 
y = df["Churn"] 
# 3. Entrenar modelo 
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2) 
clf = LogisticRegression(max_iter=1000) 
clf.fit(X_train, y_train) 
# 4. Guardar modelo 
joblib.dump(clf, "churn_model.pkl") 