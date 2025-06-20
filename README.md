# It's not a Tumah!

Demo code for Monty on Ultrasound data. Project produced during TBP Robot Hackathon 2025.

<img src="https://ih1.redbubble.net/image.926924257.3854/bg,f8f8f8-flat,750x,075,f-pad,750x1000,f8f8f8.jpg" width="200">

## Installation

The environment for this project is managed with [conda](https://www.anaconda.com/download/success).

To create the environment, run:

### ARM64 (Apple Silicon) (zsh shell)
```
conda env create -f environment.yml --subdir=osx-64
conda init zsh
conda activate itsnotatumah
conda config --env --set subdir osx-64
```

### ARM64 (Apple Silicon) (bash shell)
```
conda env create -f environment.yml --subdir=osx-64
conda init
conda activate itsnotatumah
conda config --env --set subdir osx-64
```

### Intel (zsh shell)
```
conda env create -f environment.yml
conda init zsh
conda activate itsnotatumah
```

### Intel (bash shell)
```
conda env create -f environment.yml
conda init
conda activate itsnotatumah
```

## Experiments

Experiments are defined in the `configs` directory.

After installing the environment, to run an experiment, run:

```bash
python run.py -e <experiment_name>
```

To run training on an offline ultrasound dataset (.json files) run:
```bash
python run.py -e json_dataset_ultrasound_learning
```

Make sure the `data_path` in `env_init_args` of the `json_dataset_ultrasound_learning` config points to your dataset.

TODO: Add instructions for downloading dataset.

To run inference on an offline ultrasound dataset (.json files) run:
```bash
python run.py -e json_dataset_ultrasound_experiment
```
(again, making sure the `data_path` points to your dataset)

To run an interactive, live Ultrasound experiment, run:
```bash
python run.py -e probe_triggered_experiment
```

To run a live Ultrasound experiment to collect a new .json dataset, run:
```bash
python run.py -e probe_triggered_data_collection_experiment
```

## Development

After installing the environment, you can run the following commands to check your code.

### Run formatter

```bash
ruff format
```

### Run style checks

```bash
ruff check
```

### Run dependency checks

```bash
deptry .
```

### Run static type checks

```bash
mypy .
```

### Run tests

```bash
pytest
```
