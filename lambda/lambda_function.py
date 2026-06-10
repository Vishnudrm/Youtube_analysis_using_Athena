import awswrangler as wr
import pandas as pd
import urllib.parse
import os
from typing import Dict, Any

# Environment variables
S3_CLEANSED_LAYER = os.environ.get("s3_cleansed_layer")
GLUE_DB = os.environ.get("glue_catalog_db_name")
GLUE_TABLE = os.environ.get("glue_catalog_table_name")
WRITE_MODE = os.environ.get("write_data_operation", "append")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process YouTube category reference JSON files and convert to Parquet.
    
    Args:
        event: S3 ObjectCreated event from S3 Notifications
        context: Lambda runtime context
        
    Returns:
        Response with processing status and metadata
        
    Raises:
        Exception: On JSON parsing, transformation, or S3 write failures
    """
    
    try:
        # Extract S3 bucket and key from event
        bucket = event["Records"][0]["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(
            event["Records"][0]["s3"]["object"]["key"],
            encoding="utf-8"
        )
        
        print(f"Processing: s3://{bucket}/{key}")
        
        # Read raw JSON from S3
        df_raw = wr.s3.read_json(path=f"s3://{bucket}/{key}")
        print(f"Raw records read: {len(df_raw)}")
        
        # Flatten nested JSON structure
        df_normalized = pd.json_normalize(
            df_raw["items"],
            max_level=2
        )
        print(f"Normalized records: {len(df_normalized)}")
        print(f"Columns: {df_normalized.columns.tolist()}")
        
        # Remove columns with all null values
        df_normalized = df_normalized.dropna(axis=1, how='all')
        
        # Write to Parquet with Glue metadata
        response = wr.s3.to_parquet(
            df=df_normalized,
            path=S3_CLEANSED_LAYER,
            dataset=True,
            database=GLUE_DB,
            table=GLUE_TABLE,
            mode=WRITE_MODE,
            compression="snappy"
        )
        
        print(f"Parquet write successful: {response}")
        
        return {
            "statusCode": 200,
            "body": {
                "message": "Data processing completed successfully",
                "records_processed": len(df_normalized),
                "output_path": S3_CLEANSED_LAYER
            }
        }
        
    except KeyError as e:
        print(f"Invalid event structure: {str(e)}")
        raise e
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        raise e
