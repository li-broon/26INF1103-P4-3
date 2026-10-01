import pandas as pd
import os

DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_FILE = os.path.join(DATA_FOLDER, "data.csv")

def save_data_to_csv(data, file_path):
    """
    Save the given data to a CSV file.

    Parameters:
    data (pd.DataFrame): The data to be saved.
    file_path (str): The path where the CSV file will be saved.
    """

    # Create the directory if the file path exists
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name)

    # Create dataframe for data and save to CSV
    df = pd.DataFrame(data)

    # Check if file exists to determine if we need to write headers, 
    # and use mode='a' to append data instead of overwriting the whole file
    file_exists = os.path.exists(file_path)
    df.to_csv(file_path, mode='a', header=not file_exists, index=False)

def load_data_from_csv(file_path):
    """
    Loads data from CSV file and sends success or error message.

    Parameters:
    file_path (str): The path of the CSV file to load.

    Returns:
    pd.DataFrame: The loaded data, or None if loading failed.
    """

    try:
        df = pd.read_csv(file_path)
        print(f"Success: loaded data from '{file_path}'.")
        return df
    #Removing the first two errors for now, add back if needed
    #except FileNotFoundError:
    #    print(f"Error: the file '{file_path}' does not exist.")
    #except pd.errors.EmptyDataError:
    #    print(f"Error: the file '{file_path}' is empty.")
    except pd.errors.ParserError:
        print(f"Error: the file '{file_path}' is not a valid CSV or is badly formatted.")
    except PermissionError:
        print(f"Error: you don't have permission to read '{file_path}'.")
    except Exception as e:
        print(f"Error: an unexpected problem occurred while loading '{file_path}': {e}")

    return None

def sort_by_column(data, column_name):
    """
    Sort the given data by the specified column.

    Parameters:
    data (pd.DataFrame): The data to be sorted.
    column_name (str): The name of the column to sort by.

    Returns:
    pd.DataFrame: The sorted data.
    """
    return data.sort_values(by=column_name)