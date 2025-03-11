# -*- coding: utf-8 -*-
"""Terrafarm.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1XRofYQh8RUQG_ZdzvwyBoVU_gumKfr7v
"""

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split, cross_val_score, KFold, GridSearchCV
from sklearn.preprocessing import StandardScaler, MinMaxScaler

# Load the data
data = pd.read_csv('data.csv')

# Min-Max normalization for Rainfall and Population
data['Normalized Rainfall'] = (data['Average Annual Rainfall (inches)'] - data['Average Annual Rainfall (inches)'].min()) / (data['Average Annual Rainfall (inches)'].max() - data['Average Annual Rainfall (inches)'].min())

data['Normalized Population'] = (data['Population'] - data['Population'].min()) / (data['Population'].max() - data['Population'].min())\

data['Normalized Area'] = (data['Area available for afforestation (acres)'] - data['Area available for afforestation (acres)'].min()) / (data['Area available for afforestation (acres)'].max() - data['Area available for afforestation (acres)'].min())

data['afforestation_score'] = (
    0.3 * data['Normalized Rainfall'] +
    0.35 * data['Soil Suitability (0 to 1)'] +
    0.1 * data['Wildlife Benefit Potential (0 to 1)'] -
    0.08 * np.sqrt(data['Normalized Population']) +  # Nonlinear penalty
    0.07 * data['Normalized Area'] +
    0.1 * data['Lack of tree cover']
)

print(data["afforestation_score"].describe())

# Define a reasonable raw score threshold based on domain knowledge
raw_threshold = 0.5 # Adjust this based on your data
data["good_for_afforestation"] = (data["afforestation_score"] > raw_threshold).astype(int)

# Select features for modeling
features = ['Normalized Rainfall', 'Soil Suitability (0 to 1)',
           'Wildlife Benefit Potential (0 to 1)', 'Normalized Population',
            'Normalized Area','Lack of tree cover']

X = data[features]
y = data['good_for_afforestation']

X_temp, X_test, y_temp, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42
)
X_train, X_val, y_train, y_val = train_test_split(
    X_temp, y_temp, test_size=0.15, random_state=42
)

# Standardize the features
scaler = MinMaxScaler()
X_train = scaler.fit_transform(X_train)
X_val = scaler.transform(X_val)
X_test = scaler.transform(X_test)

print(X_train[:5])  # Show first 5 rows
print(X_test[:5])   # Show first 5 rows

# Set up cross-validation
kfold = KFold(n_splits=5, shuffle=True, random_state=42)

# Define base XGBoost model
base_model = xgb.XGBClassifier(
    objective="binary:logistic",
    random_state=42
)

# Perform cross-validation
cv_scores = cross_val_score(base_model, X_train, y_train, cv=kfold, scoring='accuracy')
print("\nCross-validation scores:", cv_scores)
print(f"Mean CV accuracy: {cv_scores.mean():.4f}")
print(f"CV standard deviation: {cv_scores.std():.4f}")

param_grid = {
    'max_depth': [3, 4, 5],
    'learning_rate': [0.05, 0.1, 0.2],
    'n_estimators': [50, 100, 150],
    'subsample': [0.8, 0.9, 1.0]
}

grid_search = GridSearchCV(
    estimator=base_model,
    param_grid=param_grid,
    cv=kfold,
    scoring='accuracy',
    verbose=1
)

grid_search.fit(X_train, y_train)
print("\nBest parameters:", grid_search.best_params_)
print(f"Best cross-validation score: {grid_search.best_score_:.4f}")

# Train the final model with the best parameters on the combined training and validation sets
best_model = grid_search.best_estimator_
X_train_val = np.vstack((X_train, X_val))
y_train_val = pd.concat([y_train, y_val])

best_model.fit(X_train_val, y_train_val)

# Validate on the validation set before final testing
val_predictions = best_model.predict(X_val)
print("\nValidation Set Results:")
print(f"Accuracy: {accuracy_score(y_val, val_predictions):.4f}")
print("\nValidation Classification Report:")
print(classification_report(y_val, val_predictions))

# Final evaluation on the test set
test_predictions = best_model.predict(X_test)
print("\nTest Set Results:")
print(f"Accuracy: {accuracy_score(y_test, test_predictions):.4f}")
print("\nTest Classification Report:")
print(classification_report(y_test, test_predictions))

# Function to get afforestation suitability by state
def get_afforestation_locations(state, model, features):
    """
    Input: State name
    Output: List of suitable locations for afforestation in the specified state.
    """
    state_data = data[data["State"] == state].copy()

    if state_data.empty:
        return f"No data available for {state}."

    # Prepare features for prediction
    X_state = state_data[features]

    # Predict suitability
    predictions = model.predict(X_state)
    probabilities = model.predict_proba(X_state)[:, 1]  # Probability of class 1

    # Add predictions to the state data
    state_data["Prediction"] = predictions
    state_data["Probability"] = probabilities

    # Filter for good locations (Prediction == 1)
    good_locations = state_data[state_data["Prediction"] == 1]

    if good_locations.empty:
        return f"No suitable locations found for afforestation in {state}."

    # Return only the location names
    return good_locations[["City", "Probability"]].sort_values(by="Probability", ascending=False)

# Basic Input-Output system
def main():
    state_input = input("Enter the state you want to check for afforestation suitability: ")
    result = get_afforestation_locations(state_input, best_model, features)

    if isinstance(result, str):  # If the result is a message (e.g., "No data available")
        print(result)
    else:
        print(f"Suitable locations for afforestation in {state_input}:")
        for index, row in result.iterrows():
            print(f"- {row['City']} (Probability: {row['Probability']:.4f})")

def predict_afforestation_suitability(model):
    # Create a feature array for the new location
    rainfall = float(input("Enter rainfall in inches : "))
    soil_suitability = float(input("Enter soil suitability (0 to 1) : "))
    wildlife_potential = float(input("Enter wildlife potential (0 to 1) : "))
    population = float(input("Enter population : "))
    lack_of_tree_cover = float(input("Enter lack of tree cover (0 to 1) : "))
    area = float(input("Enter area available for afforestation (acres) : "))
    new_location = np.array(
        [[rainfall, soil_suitability, wildlife_potential, population, lack_of_tree_cover, area]]
    )

    # Make prediction
    prediction = model.predict(new_location)[0]
    probability = model.predict_proba(new_location)[0][1]

    if prediction == 1:
        suitability = "Good"
    else:
        suitability = "Not Good"

    return suitability, probability

if __name__ == "__main__":
    print("1. Select Location From Database")
    print("2. Predict New Location")
    print("3. Exit")

    while True:
        choice = int(input("Enter your choice: "))

        if choice == 1:
            main()  # Calls main() if user selects option 1

        elif choice == 2:
            result = predict_afforestation_suitability(best_model)  # Call the function
            print(f"Prediction Result: {result}")  # Print the returned result

        elif choice == 3:
            print("Exiting...")
            break  # Exit the loop

        else:
            print("Invalid choice! Please enter 1, 2, or 3.")

