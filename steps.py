
INTRO = """
HQ acts as the hub for information flow in this scenario. It is where the data is collected from various sources (we simulate NASA feed),
processed and distributed to various targets, including the field teams working at the edge, as actionable intelligence.
Microservice status for Headquarters are shown above.
You can pause/resume them on clicking their icon. The numbers indicate the processed items for each service.
We are going to start and explain each service in the following steps.
"""

INGESTION = """
Let's start with generating sample data mocking RSS feed from NASA.
We are using pre-recorded images from 2014, but we can also get them in real-time using the relevant NASA API calls.
For each message we recieve, we will create a record in the JSON Table and
send a message to the pipeline to inform the next service, Image Download, so it can process the message content.
"""

ETL = """
With each message in the pipeline, we will get a link to download the asset. We will download this asset,
and save the image in a volume, while updating the location of the asset in the database.
"""

