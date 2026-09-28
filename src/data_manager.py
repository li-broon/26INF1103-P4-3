import pandas as pd
import os

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
    df.to_csv(file_path, index=False)
