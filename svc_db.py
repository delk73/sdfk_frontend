from datetime import datetime
import json
import os
import logging
from typing import Dict, Optional, Union, List
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor
from azure.identity import ManagedIdentityCredential
import sqlite3
from dotenv import load_dotenv

from urllib.parse import urlparse

from models import SDFKColorCurve
# File path for the SQLite database
SQLITE_DB_PATH = os.path.join("/home/site/wwwroot", "local_cache.db")

load_dotenv()

def get_postgres_connection():
    try:
        connection = psycopg2.connect(
            dbname=os.getenv('POSTGRES_DB'),
            user=os.getenv('POSTGRES_USER'),
            password=os.getenv('POSTGRES_PASSWORD'),
            host=os.getenv('POSTGRES_HOST'),
            port=int(os.getenv('POSTGRES_PORT')),  # Ensure the port is cast to an integer
            sslmode='require'
        )
        logging.info("PostgreSQL connection established successfully.")
        return connection
    except Exception as e:
        logging.error(f"Failed to connect to PostgreSQL: {e}")
        raise
    
def execute_query(query: str, params: tuple = ()):
    """
    Execute a query on the PostgreSQL database.
    :param query: SQL query string.
    :param params: Tuple of parameters for the query.
    :return: Query result.
    """
    connection = None
    try:
        connection = get_postgres_connection()
        cursor = connection.cursor()
        
        # Log the query and parameters for tracking in App Insights
        logging.info(f"Executing query: {query} with params: {params}")
        
        # Execute the query
        cursor.execute(query, params)
        
        # Fetch all results
        result = cursor.fetchall()
        logging.info(f"Query executed successfully. Fetched {len(result)} rows.")
        
        return result

    except Exception as e:
        # Log the error for tracking in App Insights
        logging.error(f"Error executing query: {query} with params: {params}. Error: {e}")
        raise
    finally:
        if connection:
            cursor.close()
            connection.close()
            logging.info("PostgreSQL connection closed.")

def execute_query_sl(query, params=()):
    try:
        connection = get_postgres_connection()
        # Use RealDictCursor for dictionary-like results
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            result = cursor.fetchall()
            return result
    except Exception as e:
        print(f"Error executing query: {e}")
        raise
    finally:
        if connection:
            connection.close()

def execute_raw_query(query: str):  
    """  
    Execute a raw SQL query on the PostgreSQL database.  
      
    :param query: SQL query string.  
    :return: Query result.  
    """  
    connection = None  
    try:  
        connection = get_postgres_connection()  
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:  
            # Log the raw query for tracking  
            logging.info(f"Executing raw query: {query}")  
            cursor.execute(query)  
            result = cursor.fetchall()  
            return result  
    except Exception as e:  
        logging.error(f"Error executing raw query: {query}. Error: {e}")  
        raise  
    finally:  
        if connection:  
            connection.close()  
            logging.info("PostgreSQL connection closed.")  

def count_records(table_name: str, condition: str = None) -> int:  
    """  
    Count the number of records in a specified table, optionally applying a condition.  
      
    :param table_name: The name of the table to count records from.  
    :param condition: Optional SQL condition to apply (e.g., "name IS NULL").  
    :return: The count of records matching the condition.  
    """  
    connection = None  
    try:  
        connection = get_postgres_connection()  
        cursor = connection.cursor()  
          
        # Build the SQL query  
        query = f"SELECT COUNT(*) FROM {table_name}"  
        if condition:  
            query += f" WHERE {condition};"  
          
        # Log the query for tracking  
        logging.info(f"Executing count query: {query}")  
          
        # Execute the query  
        cursor.execute(query)  
          
        # Fetch the result (expecting a single row with a single column)  
        result = cursor.fetchone()  
        logging.info(f"Count query executed successfully. Result: {result}")  
          
        # Return the count or zero if the result is None  
        return result[0] if result is not None else 0  
  
    except Exception as e:  
        # Log the error for tracking  
        logging.error(f"Error counting records in {table_name}: {e}")  
        return 0  
  
    finally:  
        if connection:  
            cursor.close()  
            connection.close()  
            logging.info("PostgreSQL connection closed.")

    
def execute_non_select_query(query: str, params: tuple = ()) -> int:
    """
    Execute a non-SELECT query (e.g., UPDATE, INSERT, DELETE) on the PostgreSQL database.
    :param query: SQL query string.
    :param params: Tuple of parameters for the query.
    :return: Number of affected rows.
    """
    connection = None
    try:
        connection = get_postgres_connection()
        cursor = connection.cursor()
        
        logging.info(f"Executing Non-SELECT query: {query} with params: {params}")
        cursor.execute(query, params)
        connection.commit()
        
        affected_rows = cursor.rowcount
        logging.info(f"Query executed successfully. Affected rows: {affected_rows}.")
        return affected_rows

    except Exception as e:
        logging.error(f"Error executing Non-SELECT query: {query} with params: {params}. Error: {e}")
        raise
    finally:
        if connection:
            cursor.close()
            connection.close()
            logging.info("PostgreSQL connection closed.")


# Initialize SQLite database
def get_sqlite_connection():
    try:
        connection = sqlite3.connect(SQLITE_DB_PATH)
        logging.info("SQLite connection established successfully.")
        return connection
    except Exception as e:
        logging.error(f"Failed to connect to SQLite: {e}")
        raise

def execute_sqlite_query(query: str, params: tuple = ()) -> List[Dict]:
    try:
        connection = get_sqlite_connection()
        cursor = connection.cursor()
        
        # Execute the query and fetch all results
        cursor.execute(query, params)
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in cursor.fetchall()]

        logging.info(f"SQLite query executed successfully. Retrieved {len(result)} rows.")
        return result
    except Exception as e:
        logging.error(f"Error executing SQLite query: {query} with params: {params}. Error: {e}")
        raise
    finally:
        if connection:
            connection.close()
            logging.info("SQLite connection closed.")
            
def execute_sqlite_non_select_query(query: str, params: tuple = ()) -> int:
    try:
        connection = get_sqlite_connection()
        cursor = connection.cursor()
        
        cursor.execute(query, params)
        connection.commit()
        affected_rows = cursor.rowcount

        logging.info(f"SQLite Non-SELECT query executed. Affected rows: {affected_rows}")
        return affected_rows
    except Exception as e:
        logging.error(f"Error executing SQLite non-select query: {query} with params: {params}. Error: {e}")
        raise
    finally:
        if connection:
            connection.close()
            logging.info("SQLite connection closed.")



def insert_color_curve_record(sdfk_color_curve):
    query = """
    INSERT INTO Color_Curves (
        uuid,
        name, description, thumbnail_url, curve_json_url, search_json_url,
        R_float_curve_type, R_resolution_scale, R_noise_scale,
        G_float_curve_type, G_resolution_scale, G_noise_scale,
        B_float_curve_type, B_resolution_scale, B_noise_scale,
        A_float_curve_type, A_resolution_scale, A_noise_scale,
        meta_x_offset_curve_type, meta_y_offset_curve_type,
        meta_x_offset_scale, meta_y_offset_scale,
        meta_x_resolution_scale, meta_y_resolution_scale,
        meta_x_noise_scale, meta_y_noise_scale,
        created_at, updated_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s,
        %s, %s,
        %s, %s,
        %s, %s,
        %s, %s,
        %s, %s
    )
    ON CONFLICT (uuid) DO UPDATE SET
        name = EXCLUDED.name,
        description = EXCLUDED.description,
        thumbnail_url = EXCLUDED.thumbnail_url,
        curve_json_url = EXCLUDED.curve_json_url,
        search_json_url = EXCLUDED.search_json_url,
        R_float_curve_type = EXCLUDED.R_float_curve_type,
        R_resolution_scale = EXCLUDED.R_resolution_scale,
        R_noise_scale = EXCLUDED.R_noise_scale,
        G_float_curve_type = EXCLUDED.G_float_curve_type,
        G_resolution_scale = EXCLUDED.G_resolution_scale,
        G_noise_scale = EXCLUDED.G_noise_scale,
        B_float_curve_type = EXCLUDED.B_float_curve_type,
        B_resolution_scale = EXCLUDED.B_resolution_scale,
        B_noise_scale = EXCLUDED.B_noise_scale,
        A_float_curve_type = EXCLUDED.A_float_curve_type,
        A_resolution_scale = EXCLUDED.A_resolution_scale,
        A_noise_scale = EXCLUDED.A_noise_scale,
        meta_x_offset_curve_type = EXCLUDED.meta_x_offset_curve_type,
        meta_y_offset_curve_type = EXCLUDED.meta_y_offset_curve_type,
        meta_x_offset_scale = EXCLUDED.meta_x_offset_scale,
        meta_y_offset_scale = EXCLUDED.meta_y_offset_scale,
        meta_x_resolution_scale = EXCLUDED.meta_x_resolution_scale,
        meta_y_resolution_scale = EXCLUDED.meta_y_resolution_scale,
        meta_x_noise_scale = EXCLUDED.meta_x_noise_scale,
        meta_y_noise_scale = EXCLUDED.meta_y_noise_scale,
        updated_at = EXCLUDED.updated_at;
    """
    try:
        data = (
            sdfk_color_curve.uuid,
            sdfk_color_curve.name,
            sdfk_color_curve.description or '',
            sdfk_color_curve.thumbnail_url or None,
            sdfk_color_curve.curve_json_url or None,
            sdfk_color_curve.search_json_url or None,
            sdfk_color_curve.R_float_curve_type,
            sdfk_color_curve.R_resolution_scale,
            sdfk_color_curve.R_noise_scale,
            sdfk_color_curve.G_float_curve_type,
            sdfk_color_curve.G_resolution_scale,
            sdfk_color_curve.G_noise_scale,
            sdfk_color_curve.B_float_curve_type,
            sdfk_color_curve.B_resolution_scale,
            sdfk_color_curve.B_noise_scale,
            sdfk_color_curve.A_float_curve_type,
            sdfk_color_curve.A_resolution_scale,
            sdfk_color_curve.A_noise_scale,
            sdfk_color_curve.meta_x_offset_curve_type,
            sdfk_color_curve.meta_y_offset_curve_type,
            sdfk_color_curve.meta_x_offset_scale,
            sdfk_color_curve.meta_y_offset_scale,
            sdfk_color_curve.meta_x_resolution_scale,
            sdfk_color_curve.meta_y_resolution_scale,
            sdfk_color_curve.meta_x_noise_scale,
            sdfk_color_curve.meta_y_noise_scale,
            sdfk_color_curve.created_at,
            sdfk_color_curve.updated_at
        )

        # Connect and execute
        connection = get_postgres_connection()
        cursor = connection.cursor()
        cursor.execute(query, data)
        connection.commit()
        cursor.close()
        connection.close()

        logging.info(f"Inserted or updated record for curve '{sdfk_color_curve.uuid}' in the database.")

    except Exception as e:
        logging.error(f"Failed to insert or update record in the database: {e}")
        raise


def fetch_model_config(model_name: str) -> Optional[Dict[str, str]]:
    """
    Fetch model-specific configuration details from the models table.

    Args:
        model_name (str): The name of the model (e.g., 'gpt-3.5-turbo-instruct').

    Returns:
        Dict[str, str]: A dictionary with configuration details (e.g., endpoint_url base url and api vbersion also for composing client conns).
    """
    query = """
        SELECT model_id, model_name, endpoint_url, api_key_variable_name, average_score, success_rate, api_version, base_url
        FROM models
        WHERE model_name = %s
        LIMIT 1;
    """
    params = (model_name,)

    try:
        result = execute_query_sl(query, params)
        if result:
            logging.info(f"Fetched configuration for model: {model_name}")
            return result[0]
        else:
            logging.warning(f"No configuration found for model: {model_name}")
            return None
    except Exception as e:
        logging.error(f"Error fetching model configuration: {e}")
        return None
    

def log_exception(related_id, operation, error_message, error_code, result_data=None):
    """
    Logs an exception into the 'exceptions' table.
    """
    try:
        insert_query = """
            INSERT INTO exceptions (
                exception_id, 
                related_table, 
                related_id, 
                operation, 
                error_message, 
                error_code, 
                resolved, 
                resolution_notes
            )
            VALUES (gen_random_uuid(), 'Color_Curves', %s, %s, %s, %s, FALSE, %s)
        """
        resolution_notes = json.dumps(result_data) if result_data else None
        execute_non_select_query(insert_query, (related_id, operation, error_message, str(error_code), resolution_notes))
        logging.info(f"Exception logged for UUID: {related_id}, Operation: {operation}.")
    except Exception as e:
        logging.error(f"Failed to log exception: {e}")


def fetch_records(table_name, limit=None, offset=None):
    """
    Fetch records from the specified table with pagination.
    Only fetch the 'name' column where the 'name' contains at least one comma.
    Order the results randomly.
    
    Args:
        table_name (str): Name of the table to fetch records from.
        limit (int, optional): Maximum number of records to fetch. Defaults to None.
        offset (int, optional): Number of records to skip before starting to fetch. Defaults to None.
    
    Returns:
        list: List of records.
    """
    query = f"SELECT * FROM {table_name} WHERE name NOT LIKE %s ORDER BY RANDOM()"
    params = ['%,%']
    
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)
    
    if offset is not None:
        query += " OFFSET %s"
        params.append(offset)
    
    try:
        records = execute_query_sl(query, tuple(params))
        return records
    except Exception as e:
        logging.error(f"Error fetching records: {e}")
        return []


def fetch_work_records(table_name, limit=None, offset=None):
    """
    Fetch records from the specified table with pagination.
    Only fetch the 'name' column where the 'name' contains at least one comma.
    Order the results randomly.
    
    Args:
        table_name (str): Name of the table to fetch records from.
        limit (int, optional): Maximum number of records to fetch. Defaults to None.
        offset (int, optional): Number of records to skip before starting to fetch. Defaults to None.
    
    Returns:
        list: List of records.
    """
    query = f"SELECT * FROM {table_name} WHERE name LIKE %s"
    params = ['%,%']
    
    if limit is not None:
        query += " LIMIT %s"
        params.append(limit)
    
    if offset is not None:
        query += " OFFSET %s"
        params.append(offset)
    
    try:
        records = execute_query_sl(query, tuple(params))
        return records
    except Exception as e:
        logging.error(f"Error fetching records: {e}")
        return []


def fetch_records_by_uuids(uuids, table_name, limit=None, offset=None):
    """
    Fetch records by UUIDs from the specified table.
    
    Args:
        uuids (list): List of UUIDs to fetch.
        table_name (str): Name of the table to fetch records from.
        limit (int, optional): Maximum number of records to fetch. Defaults to None.
        offset (int, optional): Number of records to skip before starting to fetch. Defaults to None.
    
    Returns:
        list: List of records.
    """
    query = f"SELECT * FROM {table_name} WHERE uuid IN %s"
    params = (tuple(uuids),)
    
    if limit is not None:
        query += " LIMIT %s"
        params += (limit,)
    
    if offset is not None:
        query += " OFFSET %s"
        params += (offset,)
    
    try:
        records = execute_query_sl(query, params)
        return records
    except Exception as e:
        logging.error(f"Error fetching records by UUIDs: {e}")
        return []
    
def update_field(uuid, table_name, field_name, new_value):
    """
    Updates the specified field with a new value for the given UUID and logs the action to `column_action_log`.
    """
    response = {
        "status": "error",
        "message": "",
        "data": {}
    }

    # Fetch the current value before updating for logging purposes
    select_query = f"SELECT {field_name} FROM {table_name} WHERE uuid = %s;"
    try:
        current_value = execute_query_sl(select_query, (uuid,))[0].get(field_name)
    except Exception as e:
        response["message"] = f"Error fetching current value of {field_name} for UUID {uuid}: {e}"
        logging.error(response["message"])
        return response

    # Update the specified field
    update_query = f"""
        UPDATE {table_name}
        SET {field_name} = %s
        WHERE uuid = %s;
    """
    try:
        execute_non_select_query(update_query, (new_value, uuid))
        logging.info(f"Successfully updated {field_name} for UUID: {uuid}")

        # Log the update action to `column_action_log`
        log_query = """
            INSERT INTO column_action_log (uuid, action_type, column_name, old_value, new_value, reason, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        # Define parameters for logging
        log_params = (
            uuid,                  # uuid of the record
            'update',              # action type
            field_name,            # column that was updated
            current_value,         # old value before the update
            new_value,             # new value after the update
            f"Updated {field_name} to new value",  # reason for the update
            'admin'                # Static value for created_by
        )
        execute_non_select_query(log_query, log_params)
        
        response["status"] = "success"
        response["message"] = f"Successfully updated {field_name} for UUID: {uuid}"
        response["data"] = {
            "uuid": uuid,
            "field_name": field_name,
            "old_value": current_value,
            "new_value": new_value
        }
        return response

    except Exception as e:
        response["message"] = f"Error updating {field_name} in the database or logging action: {e}"
        logging.error(response["message"])
        return response