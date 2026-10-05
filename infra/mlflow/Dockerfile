# Built from python:slim so it runs on the ARM (aarch64) VM, with the Postgres and S3 drivers
# that the stock MLflow image does not include.
FROM python:3.12-slim
RUN pip install --no-cache-dir "mlflow==2.17.2" "psycopg2-binary==2.9.9" "boto3==1.35.36"
EXPOSE 5000
