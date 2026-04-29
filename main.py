import json

class SheetstoJSON:
    def __init__(self):
        pass

# Function to convert the class objects to a dictionary
    def convert_to_dict(self,obj):
        # If obj is a list, we need to iterate over the list and convert each element
        if isinstance(obj, list):
            return [self.convert_to_dict(item) for item in obj]
        # If obj is a dict, return it as-is
        elif isinstance(obj, dict):
            return obj
        # If obj is a class instance (Sheet, Column, Error), convert its attributes to a dictionary
        elif hasattr(obj, '__dict__'):
            return {key: self.convert_to_dict(value) for key, value in obj.__dict__.items() if value is not None}
        else:
            # Base case for attributes that are not objects (like str, int, etc.)
            return obj

    # Function to convert list of Sheets into the desired dictionary format for JSON
    def sheets_to_dict(self, sheets):
        # Creating a "Sheets" key containing all the sheet objects
        return {"Sheets": [self.convert_to_dict(sheet) for sheet in sheets]}
