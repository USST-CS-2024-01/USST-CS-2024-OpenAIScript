import os

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "password")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "scs_backend")

KAFKA_HOST = os.environ.get("KAFKA_HOST", "localhost")
KAFKA_PORT = int(os.environ.get("KAFKA_PORT", 9092))
KAFKA_TOPIC = os.environ.get("KAFKA_TOPIC", "scs-ai_doc_evaluation")
