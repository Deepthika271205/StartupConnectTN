from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Training sample dataset for domain classification
descriptions = [
    "AI based crop disease detection using machine learning",
    "Blockchain payment system for digital transactions",
    "Online hospital appointment and telemedicine system",
    "Machine learning fraud detection for banking",
    "Digital banking platform with mobile wallet",
    "Smart irrigation system for farmers",
    "E-learning platform for students",
    "Online marketplace for local products",
    "Healthcare monitoring wearable device",
    "Agricultural drone for crop monitoring"
]

labels = [
    "AgriTech",
    "FinTech",
    "HealthTech",
    "FinTech",
    "FinTech",
    "AgriTech",
    "EdTech",
    "E-Commerce",
    "HealthTech",
    "AgriTech"
]

# Initialize and train the model
vectorizer = TfidfVectorizer(max_features=100)
X = vectorizer.fit_transform(descriptions)

model = LogisticRegression(max_iter=200)
model.fit(X, labels)

def predict_domain(text):
    """Predict startup domain using ML model"""
    try:
        vec = vectorizer.transform([text])
        return model.predict(vec)[0]
    except:
        return "Other"

def match_mentors_ml(idea_text, mentor_interests):
    """Match mentors using cosine similarity"""
    try:
        if not mentor_interests:
            return []
        
        texts = [idea_text] + mentor_interests
        vec = vectorizer.transform(texts)
        
        similarities = cosine_similarity(vec[0:1], vec[1:])
        return similarities[0].tolist()
    except:
        return [0] * len(mentor_interests)

def calculate_risk_score(growth_rate, revenue, burn_rate):
    """Calculate investor risk score"""
    if growth_rate > 20 and burn_rate < revenue:
        return "Low", 85
    elif growth_rate > 10 and burn_rate < revenue * 1.5:
        return "Medium", 60
    else:
        return "High", 35
