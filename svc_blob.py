# blob_service.py

import os
import logging
from azure.identity import ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient
import concurrent

import requests

def get_blob_service_client() -> BlobServiceClient:
    storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "sasdfk")
    
    if not storage_account_name:
        logging.error("AZURE_STORAGE_ACCOUNT_NAME is not set or is empty.")
        raise ValueError("AZURE_STORAGE_ACCOUNT_NAME is not set.")
    
    storage_account_url = f"https://{storage_account_name}.blob.core.windows.net"
    logging.info(f"Using storage account URL: {storage_account_url}")
    
    managed_identity_client_id = os.getenv("AZURE_CLIENT_ID")
    if not managed_identity_client_id:
        logging.error("AZURE_CLIENT_ID is not set or is empty.")
        raise ValueError("AZURE_CLIENT_ID is not set.")
    
    logging.info(f"Retrieved AZURE_CLIENT_ID: {managed_identity_client_id}")
    
    credential = ManagedIdentityCredential(client_id=managed_identity_client_id)
    logging.info(f"Using user-assigned managed identity with client ID {managed_identity_client_id} for Blob Storage access.")
    
    try:
        blob_service_client = BlobServiceClient(account_url=storage_account_url, credential=credential)
        logging.info("BlobServiceClient initialized successfully.")
        return blob_service_client
    except Exception as e:
        logging.error(f"Failed to create BlobServiceClient: {e}")
        raise

# Function to fetch the JSON and PNG metadata concurrently
def fetch_blobs_metadata(json_blob_client, thumbnail_blob_client):
    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Fetch JSON content and PNG metadata in parallel
            future_json = executor.submit(json_blob_client.download_blob().readall)
            future_png_props = executor.submit(thumbnail_blob_client.get_blob_properties)

            # Wait for both futures to complete
            curve_json_data = future_json.result().decode('utf-8')
            thumbnail_properties = future_png_props.result()

            return curve_json_data, thumbnail_properties
    except Exception as e:
        logging.error(f"Error fetching metadata: {e}")
        raise

# Function to get the size of a blob
def get_blob_size(blob_client):
    """
    Retrieves the size of the specified blob in bytes.
    
    :param blob_client: The BlobClient instance for the target blob.
    :return: The size of the blob in bytes.
    """
    try:
        blob_properties = blob_client.get_blob_properties()
        blob_size = blob_properties.size
        logging.info(f"Blob size for {blob_client.blob_name}: {blob_size} bytes")
        return blob_size
    except Exception as e:
        logging.error(f"Error retrieving blob size for {blob_client.blob_name}: {e}")
        raise


def fetch_json(url):
    """
    Fetches and parses JSON data from the given URL.

    Args:
        url (str): The URL to fetch the JSON data from.

    Returns:
        dict: A dictionary containing the status, message, and data.
    """
    response_data = {
        "status": "error",
        "message": "",
        "data": None
    }

    try:
        response = requests.get(url)
        response.raise_for_status()
        response_data["status"] = "success"
        response_data["message"] = "Successfully fetched JSON data."
        response_data["data"] = response.json()
    except requests.RequestException as e:
        response_data["message"] = f"Failed to fetch JSON data: {e}"

    return response_data 