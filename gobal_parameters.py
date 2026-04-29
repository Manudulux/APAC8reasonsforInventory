import re, os
from src.helper import S2J
from .J2S import JSONtoSheets

def get_base_path():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Validation:
    def __init__(self):
        pass

    def validatesheets(self, input):
        try:
            file_dir = os.path.join(get_base_path(), 'data')
            config = JSONtoSheets().readconfig(os.path.join(file_dir, 'config.json'))
            for config_sheet in config:
                for input_sheet in input:
                    if input_sheet.Name:
                        if input_sheet.Name == config_sheet.Variable or input_sheet.Name == config_sheet.Name:
                            config_sheet.Data = input_sheet.Data
                            config_sheet.FileName = input_sheet.FileName
                            break
                    else:
                        match = re.search(config_sheet.NameExpression, input_sheet.FileName)
                        if match:
                            config_sheet.Data = input_sheet.Data
                            config_sheet.FileName = input_sheet.FileName
                            break
            for config_sheet_2 in config:
                if config_sheet_2.FileName is None:
                    error = {"Code": 401, "Description": "Missing input Excel file"}
                    config_sheet_2.Errors.append(error)
            result = S2J.SheetstoJSON().sheets_to_dict(config)
            return result
        except Exception as e:
            return str(e)
