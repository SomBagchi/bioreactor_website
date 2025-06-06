FROM python:3.10-slim

RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

RUN pip install --no-cache-dir numpy pandas scikit-learn matplotlib

CMD ["python"]
