import json
import logging
import pymysql
import requests
from kafka import KafkaConsumer
import openai
from config import KAFKA_TOPIC, KAFKA_HOST, KAFKA_PORT, MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, \
    MYSQL_DATABASE

# Initialize Kafka consumer
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=f"{KAFKA_HOST}:{KAFKA_PORT}",
    client_id="python-openai-consumer"
)


# Define a function to establish a MySQL connection
def get_mysql_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )


# Initialize MySQL connection
mysql_conn = get_mysql_connection()

ERROR_TABLE = {
    -1: "Unknown error",
    -2: "Conversion timeout error",
    -3: "Conversion error",
    -4: "Error while downloading the document file to be converted",
    -5: "Incorrect password",
    -6: "Error while accessing the conversion result database",
    -7: "Input error",
    -8: "Invalid token",
    -9: "Error when the converter cannot automatically determine the output file format. "
        "This error means that the client must explicitly specify in which format the file "
        "should be converted (text document or spreadsheet). It is used to convert XML to "
        "OOXML in case the XML type is unknown",
}


def execute_with_reconnect(func):
    def wrapper(*args, **kwargs):
        global mysql_conn
        try:
            return func(*args, **kwargs)
        except pymysql.MySQLError as e:
            logging.error(f"MySQL error: {e}. Attempting to reconnect.")
            mysql_conn = get_mysql_connection()
            return func(*args, **kwargs)

    return wrapper


@execute_with_reconnect
def update_task_status(task_id, status, doc_evaluation, overall_score):
    try:
        sql = "UPDATE ai_doc_score_record SET status = %s, doc_evaluation = %s, overall_score = %s, score_time=NOW() WHERE id = %s"
        with mysql_conn.cursor() as cursor:
            cursor.execute(sql, (status, json.dumps(doc_evaluation), overall_score, task_id))
        mysql_conn.commit()
    except Exception as e:
        logging.error(f"Error updating task {task_id} status: {e}")


@execute_with_reconnect
def check_task_exist(task_id):
    try:
        sql = "SELECT COUNT(*) FROM ai_doc_score_record WHERE id = %s"
        with mysql_conn.cursor() as cursor:
            cursor.execute(sql, task_id)
            result = cursor.fetchone()
            return result[0] > 0
    except Exception as e:
        logging.error(f"Error checking task {task_id} exist: {e}")
        return False


@execute_with_reconnect
def get_config():
    options = [
        'openai:endpoint',
        'openai:secret_key',
        'openai:model',
        'openai:prompt',
    ]
    sql = f"SELECT `key`, value FROM config WHERE `key` IN ({','.join(['%s'] * len(options))})"
    with mysql_conn.cursor() as cursor:
        cursor.execute(sql, options)
        result = cursor.fetchall()
        return {r[0]: r[1] for r in result}


def start_task(message):
    try:
        data = message.decode('utf-8')
        data = json.loads(data)
        task_id = data['task_id']
        onlyoffice_url = data['onlyoffice_url']
        param = data['param']
        status = data['status']
        conf = get_config()
        if status == 'completed':
            logging.info(f"Task {task_id} already completed")
            return
        if not check_task_exist(task_id):
            logging.error(f"Task {task_id} not found")
            return
    except Exception as e:
        logging.error(f"Error processing message [{message}]: {e}")
        return

    try:
        update_task_status(task_id, 'pending', {}, 0)
        result = requests.post(onlyoffice_url, json=param,
                               headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
        if result.status_code >= 400:
            logging.error(f"Error sending document evaluation request: {result.text}")
            raise RuntimeError(f"Error sending document evaluation request: {result.text}")
        if 'error' in result.json():
            raise RuntimeError(
                f"Error sending document evaluation request: {ERROR_TABLE.get(result.json()['error'], 'Unknown error')}")
        file_url = result.json()['fileUrl']
        data = requests.get(file_url).content.decode('utf-8')
        score, comment = openai.evaluate_document(
            document=data,
            model=conf.get('openai:model'),
            endpoint=conf.get('openai:endpoint'),
            secret_key=conf.get('openai:secret_key'),
            prompt=conf.get('openai:prompt'),
        )
        update_task_status(task_id, 'completed', {"comment": comment}, score)
    except Exception as e:
        logging.error(f"Error processing task {task_id}: {e}")
        update_task_status(task_id, 'failed', {"error": str(e)}, 0)

    logging.info(f"Task {task_id} completed")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    while True:
        for msg in consumer:
            try:
                start_task(msg.value)
            except Exception as e:
                pass
