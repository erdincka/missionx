import os
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

from helpers import HQ_VOLUME_PATH, STREAM_LOCAL, TOPIC_NASAFEED

def assetdownload():
    # Create Spark session
    spark = SparkSession.builder \
        .appName("KafkaStreaming") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .getOrCreate()

    # Define Kafka parameters
    kafka_params = {
        "kafka.bootstrap.servers": f"{os.environ['MAPR_IP']}:9092",
        "subscribe": f"{STREAM_LOCAL}:{TOPIC_NASAFEED}",
        "startingOffsets": "earliest",
        "kafka.security.protocol": "SASL_PLAINTEXT",
        "kafka.sasl.mechanism": "PLAIN",
        "kafka.sasl.jaas.config": f'org.apache.kafka.common.security.plain.PlainLoginModule required username="{os.environ['MAPR_USER']}" password="{os.environ['MAPR_PASS']}";'
    }

    # Define schema for incoming Kafka messages
    schema = StructType([
        StructField("_id", IntegerType(), True),
        StructField("center", StringType(), True),
        StructField("search_term", StringType(), True),
        StructField("media_type", StringType(), True),
        StructField("date_created", StringType(), True),
        StructField("title", StringType(), True),
        StructField("nasa_id", StringType(), True),
        StructField("description", StringType(), True),
        StructField("thumbnail", StringType(), True),
    ])
    
    # Read from Kafka and apply schema
    df = spark \
    .readStream \
    .format("kafka") \
    .options(**kafka_params) \
    .option("failOnDataLoss", "false") \
    .load() \
    .selectExpr("CAST(value AS STRING)") \
    .selectExpr("SPLIT(value, ',') AS data") \
    .selectExpr(
        "data[0] AS _id",
        "data[1] AS center",
        "data[2] AS search_term",
        "data[3] AS media_type",
        "data[4] AS date_created",
        "data[5] AS title",
        "data[6] AS nasa_id",
        "data[7] AS description",
        "data[8] AS thumbnail",
    )
    
    # Define the Delta table path
    delta_table_path = f"file:///mapr/{os.environ['MAPR_CLUSTER']}/{HQ_VOLUME_PATH}/{TOPIC_NASAFEED}_delta" 

    # Define the checkpoint directory path
    checkpoint_dir = f"file:///mapr/{os.environ['MAPR_CLUSTER']}/{HQ_VOLUME_PATH}/{TOPIC_NASAFEED}_checkpoint"  

    # Write the stream to the Delta table with a processing time trigger
    query = df \
        .writeStream \
        .format("delta") \
        .outputMode("append") \
        .trigger(processingTime="1 second") \
        .option("checkpointLocation", checkpoint_dir) \
        .option("mergeSchema", "true") \
        .start(delta_table_path)

    # Wait for the termination
    query.awaitTermination(60)

    # Read from Delta table
    delta_df = spark.read.format("delta").load(delta_table_path)

    # Show the first 10 rows
    delta_df.show(10)

    # Stop Spark session
    spark.stop()
