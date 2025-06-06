# This is the Docker image for the bioreactor website.
# It is used to run the Python code on the bioreactor.
# It is based on the Python 3.10 image.
# It is used to run the Python code on the bioreactor.
# It lives on the bioreactor.
FROM python:3.10-slim

RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

RUN pip install --no-cache-dir numpy pandas scikit-learn matplotlib

CMD ["python"]
