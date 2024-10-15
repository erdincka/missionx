from glob import glob
import os
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

def spark_kafka_consumer(host: str, stream: str, topic: str):

    spark_jars = ",".join(
        [
            "/opt/mapr/spark/spark-3.3.3/jars/spark-sql-kafka-0-10_2.12-3.3.3.0-eep-921.jar",
            "/opt/mapr/spark/spark-3.3.3/jars/kafka-clients-2.6.1.700-eep-921.jar",
            "/opt/mapr/spark/spark-3.3.3/jars/kafka-eventstreams-2.6.1.700-eep-921.jar",
            "/opt/mapr/spark/spark-3.3.3/jars/spark-streaming-kafka-0-10_2.12-3.3.3.0-eep-921.jar",
            "/opt/mapr/spark/spark-3.3.3/jars/spark-token-provider-kafka-0-10_2.12-3.3.3.0-eep-921.jar",
            "/opt/mapr/spark/spark-3.3.3/jars/protobuf-java-3.21.9.jar",
            "/opt/mapr/lib/maprfs-7.7.0.0-mapr.jar",
            "/opt/mapr/lib/mapr-streams-7.7.0.0-mapr.jar",
            "/opt/mapr/lib/hadoop-common-3.3.5.300-eep-922.jar",
        ]
    )

    # Create Spark session
    spark = (
        SparkSession.builder.appName("KafkaStreaming")
        # .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        # .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        # .config("spark.jars.packages", "io.delta:delta-core_2.12:2.3.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.3.0-eep-921")
        # .config("spark.jars.packages", "io.delta:delta-core_2.12:2.3.0")
        .config("spark.jars", spark_jars)
        .getOrCreate()
    )

    # Define Kafka parameters
    kafka_params = {
        "kafka.bootstrap.servers": f"{host}:9092",
        "subscribe": f"{stream}:{topic}",
        "startingOffsets": "earliest",
        "group.id": "missionx",
        "failOnDataLoss": False,
        "maxOffsetsPerTrigger": 1000,
        "kafka.security.protocol": "SASL_PLAINTEXT",
        "kafka.sasl.mechanism": "PLAIN",
        "kafka.sasl.jaas.config": f"org.apache.kafka.common.security.plain.PlainLoginModule required username=\"{app.storage.user['MAPR_USER']}\" password=\"{app.storage.user['MAPR_PASS']}\";"
    }

    # Define schema for incoming Kafka messages
    schema = StructType([
        StructField("_id", IntegerType(), True),
        StructField("center", StringType(), True),
        StructField("search_term", StringType(), True),
        StructField("media_type", StringType(), True),
        StructField("date_created", StringType(), True),
        StructField("title", StringType(), True),
        StructField("image_id", StringType(), True),
        StructField("description", StringType(), True),
        StructField("thumbnail", StringType(), True),
    ])

    # Read from Kafka and apply schema
    df = spark \
    .readStream \
    .format("kafka") \
    .options(**kafka_params) \
    .load() \
    .selectExpr("CAST(value AS STRING)") \
    # .selectExpr("SPLIT(value, ',') AS data") \
    # .selectExpr(
    #     "data[0] AS _id",
    #     "data[1] AS center",
    #     "data[2] AS search_term",
    #     "data[3] AS media_type",
    #     "data[4] AS date_created",
    #     "data[5] AS title",
    #     "data[6] AS image_id",
    #     "data[7] AS description",
    #     "data[8] AS thumbnail",
    # )

    yield df

    # # Define the Delta table path
    # delta_table_path = f"file:///mapr/{os.environ['MAPR_CLUSTER']}/{HQ_VOLUME_PATH}/{TOPIC_IMAGEFEED}_delta"

    # # Define the checkpoint directory path
    # checkpoint_dir = f"file:///mapr/{os.environ['MAPR_CLUSTER']}/{HQ_VOLUME_PATH}/{TOPIC_IMAGEFEED}_checkpoint"

    # Write the stream to the Delta table with a processing time trigger
    query = df \
        .writeStream \
        .format("console") \
        .outputMode("append") \
        .start() \
        .awaitTermination(30)
    # .format("delta") \
    # .trigger(processingTime="1 second") \
    # .option("mergeSchema", "true") \
    # .option("checkpointLocation", checkpoint_dir) \
    # .start(delta_table_path)

    # # Wait for the termination
    # query.awaitTermination(60)

    # # Read from Delta table
    # delta_df = spark.read.format("delta").load(delta_table_path)

    # # Show the first 10 rows
    # delta_df.show(10)

    # Stop Spark session
    spark.stop()


if __name__ == "__main__":
    for a in spark_kafka_consumer("10.1.1.31", "/apps/missionX/replicatedStream", "ASSET_BROADCAST"):
        print(a)
        # pass
