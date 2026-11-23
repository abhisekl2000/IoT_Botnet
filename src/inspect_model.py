import joblib

bundle = joblib.load(
    "results/random_forest/random_forest.joblib"
)

model = bundle["model"]
features = bundle["features"]
label_mapping = bundle["label_mapping"]

print("Model:", type(model).__name__)

print("\nNumber of features:", len(features))

print("\nRequired features:")
for feature in features:
    print(feature)

print("\nLabel mapping:", label_mapping)

print("\nModel classes:", model.classes_)