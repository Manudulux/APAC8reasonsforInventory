from src.Classes.Columns import Column
from src.Classes.Sheets import Sheet
import json

class JSONtoSheets:
    def __init__(self):
        pass
    def ConvertJSONToSheets(self,json_data):
        sheets_data = []
        for sheet in json_data.get('Sheets', []):
            columns = [Column(**col) for col in sheet.get('Columns', [])]
            sheets_data.append(Sheet(
                Name=sheet.get('Name'),
                NameExpression=sheet.get('NameExpression'),
                Variable=sheet.get('Variable'),
                Columns=columns,
                Errors=sheet.get('Errors', []),
                Data=sheet.get('Data'),
                FileName=sheet.get('FileName')
            ))
        return sheets_data

    def readconfig(self,path):
        with open(path, 'r') as config_file:
            json_data = json.load(config_file)
        return self.ConvertJSONToSheets(json_data)
    
    def read_json(self, path):
        with open(path, 'r') as config:
            json_data = json.load(config)
        return json_data