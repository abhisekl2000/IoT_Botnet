## IoT_Botnet
Project for AI in Cybersecurity Course

## Setup Environment
```setup
To install project dependencies, run the following command:
make setup
```

## Run simulation
```simulation
First activate the virtual environment from IoT_Botnet/ using the following command:
source .VENV/bin/activate

Then, run the python script:
python3 src/simulation.py
```

## Run Data Pre-processing
```pre-processing
report_conflicts.py: checks the dataset for conflicting label and generates multiple reports. Use the command below to run this script:
python src/report_conflicts.py \--input data/raw/mqttdataset_reduced.csv \--output-dir results/conflicts

preprocess_mqttset.py: cleans and prepares the dataset for AI training. Use the command below to run this script:
python src.preprocess_mqttset.py \--input data/raw/mqttdataset_reduced.csv \--output-dir data/processed
```

## Train a Random Forest model to distinguish legitimate MQTT traffic from attack traffic
```train model
python src/train_model.py \--train data/processed/train_binary.csv \--test data/processed/test_binary.csv \--outputdir results/random_forest
```

## Structure
```text
IoT_Botnet
    ├── data
    │   ├── processed
    │   │   ├── preprocessing_metadata.json
    │   │   ├── test_binary.csv
    │   │   └── train_binary.csv
    │   └── raw
    │       └── mqttdataset_reduced.csv
    ├── Makefile
    ├── models
    ├── README.md
    ├── requirements.txt
    ├── results
    │   ├── conflicts
    │   │   ├── conflicts_by_class.csv
    │   │   ├── conflicts_by_mqtt_msgtype.csv
    │   │   ├── summary.txt
    │   │   └── top_100_conflicting_groups.csv
    │   └── random_forest
    │       ├── classification_report.txt
    │       ├── confusion_matrix.csv
    │       ├── confusion_matrix.png
    │       ├── feature_importance.csv
    │       ├── metrics.json
    │       └── random_forest.joblib
    └── src
        ├── iot_device.py
        ├── preprocess_mqttset.py
        ├── __pycache__
        │   └── iot_device.cpython-314.pyc
        ├── report_conflicts.py
        ├── simulation.py
        └── train_model.py

```
