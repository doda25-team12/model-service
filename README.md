# SMS Checker / Backend

The backend of this project provides a simple REST service that can be used to detect spam messages.
We have extended the base project [rohan8594/SMS-Spam-Detection](https://github.com/rohan8594/SMS-Spam-Detection), which introduces several basic classification models, and wrap one of them in a microservice.

The following sections will explain you how to get started.
The project **requires a Python 3.12 environment** to run (tested with 3.12.9).
Use the `requirements.txt` file to restore the required dependencies in your environment.


## Automated Build and Release

This repository uses GitHub Actions to automatically train, release, and containerize new model versions.

### When It Runs

The workflow automatically triggers when code is pushed to:
- `main` branch (production releases)
- Any branch starting with `test` (test releases)

### What Gets Produced

Each workflow run creates:

1. **GitHub Release** with trained model artifacts:
   - `model-{VERSION}.joblib` (e.g., `model-1.0.2.joblib`)
   - `preprocessor.joblib`
   - Semantic versioning with auto-increment (v1.0.0 → v1.0.1 → v1.0.2)

2. **Container Images** published to GitHub Container Registry (GHCR):
   - `ghcr.io/doda25-team12/model-service:v{VERSION}`
   - `ghcr.io/doda25-team12/model-service:latest` (main branch only)
   - Multi-architecture support: linux/amd64 and linux/arm64

### Using Pre-built Artifacts

**Option 1: Pull Container Image (Recommended)**

```bash
# Pull latest version
docker pull ghcr.io/doda25-team12/model-service:latest

# Run the service
docker run -e MODEL_VERSION=1.0.2 \
  -p 8081:8081 \
  ghcr.io/doda25-team12/model-service:latest

# Access the API documentation
open http://localhost:8081/apidocs
```

**Option 2: Download Model Files from Releases**

Visit [GitHub Releases](https://github.com/doda25-team12/model-service/releases) to download trained model files for specific versions.

```bash
# Example: Download and use model files
wget https://github.com/doda25-team12/model-service/releases/download/v1.0.2/model-1.0.2.joblib
wget https://github.com/doda25-team12/model-service/releases/download/v1.0.2/preprocessor.joblib
```

### Workflow Details

The automated workflow (`train-release.yml`) performs:
1. Calculates next semantic version
2. Downloads and preprocesses the SMS spam dataset
3. Trains Decision Tree classifier
4. Creates GitHub Release with model artifacts
5. Builds multi-arch Docker images
6. Publishes to GHCR with version tags

**Total runtime:** ~8-12 minutes per release


## Manual Training (Development)

For local development, experimentation, or custom model training, you can train models manually:

### Training the Model

To train the model, you have two options.
Either you create a local environment...

    $ python -m venv venv
    $ source venv/bin/activate
    $ pip install -r requirements.txt

... or you train in a Docker container (recommended):

    $ docker run -it --rm -v ./:/root/sms/ python:3.12.9-slim bash
    ... (container startup)
    $ cd /root/sms/
    $ pip install -r requirements.txt

Once all dependencies have been installed, the data can be preprocessed and the model trained by creating the output folder and invoking three commands:

    $ mkdir output
    $ python src/read_data.py
    Total number of messages:5574
    ...
    $ python src/text_preprocessing.py
    [nltk_data] Downloading package stopwords to /root/nltk_data...
    [nltk_data]   Unzipping corpora/stopwords.zip.
    ...
    $ python src/text_classification.py

The resulting model files will be placed as `.joblib` files in the `output/` folder.


### Serving Recommendations

To make the models accessible, you need to start the microservice by running the `src/serve_model.py` script from within the virtual environment that you created before, or in a fresh Docker container (recommended):

    $ docker run -it --rm -e MODEL_VERSION=0.0.1 -e MODEL_BASE_URL="url model release" -p 8081:8081 -v ./:/root/sms/ python:3.12.9-slim bash
    ... (container startup)
    $ cd /root/sms/
    $ pip install -r requirements.txt
    $ python src/serve_model.py

The server will start on port 8081.
Once its startup has finished, you can either access [localhost:8081/apidocs](http://localhost:8081/apidocs) in your browser to interact with the service, or you send `POST` requests to request predictions, for example with `curl`:


    $ curl -X POST "http://localhost:8081/predict" -H "Content-Type: application/json" -d '{"sms": "test ..."}'
    {
      "classifier": "decision tree",
      "result": "ham",
      "sms": "test ..."
    }


### Build and run the container (multi-arch capable)

From the `model-service` root folder:

```
docker buildx create --use --name multi || docker buildx use multi
docker buildx build --builder multi --platform linux/amd64,linux/arm64 -t local/model-service:dev --load .
docker run --rm -p 8081:8081 local/model-service:dev
```

