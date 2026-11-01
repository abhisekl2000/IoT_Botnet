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

## Structure
```text
IoT_Botnet/
├── Makefile
├── requirements.txt
├── README.md
├── src/
├── data/
└── models/
```
