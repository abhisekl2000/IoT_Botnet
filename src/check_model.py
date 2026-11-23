import joblib

bundle = joblib.load(
    "results/random_forest/random_forest.joblib"
)

model = bundle["model"]

print("Model:", type(model).__name__)

print("\nExpected features:")
for index, feature in enumerate(bundle["features"], 1):
    print(f"{index}. {feature}")

print("\nClasses:", model.classes_)

print(
    "Label mapping:",
    bundle.get("label_mapping", "Not available")
)