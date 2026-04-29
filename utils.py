"""This is the main Validation file"""
from src.helper.data_validator import data_validator
from src.helper.validation_helper import validator_functions
from src.helper.S2J import SheetstoJSON
from .utils import FileUtils
import pandas as pd


class Validatator:
    def __init__(self) -> None:
        """
        Created empty init. Will use if required in future.
        """
    def merge_response(self, data1, data2):
        """
        Merging both the forecast and regular files validation response
        """
        if data1 == {}:
            return data2
        elif data2 == {}:
            return data1
        # Create a new dictionary to store the merged data
        merged_data = {"Sheets": [],
                       "Missing_RM_Supplier_Pairs":data2.get('Missing_RM_Supplier_Pairs'),
                       "Missing_RM_Codes":data2.get('Missing_RM_Codes')}

        # Create a dictionary to easily lookup sheets by name
        sheets_dict1 = {sheet["Name"]: sheet for sheet in data1["Sheets"]}
        sheets_dict2 = {sheet["Name"]: sheet for sheet in data2["Sheets"]}

        # Merge the sheets
        all_sheet_names = set(sheets_dict1.keys()) | set(sheets_dict2.keys())

        for sheet_name in all_sheet_names:
            sheet1 = sheets_dict1.get(sheet_name, {"Errors": []})
            sheet2 = sheets_dict2.get(sheet_name, {"Errors": []})

            # Merge the errors
            merged_errors = sheet1.get("Errors", []) + sheet2.get("Errors", [])

            # Create the merged sheet
            merged_sheet = sheet1 if sheet_name in sheets_dict1 else sheet2
            merged_sheet["Errors"] = merged_errors

            merged_data["Sheets"].append(merged_sheet)

        return merged_data

    #insert the error in final_response python object.
    def add_error_in_sheet(self,final_response,error):
        if error:
            for sheet in final_response["Sheets"]:
                if sheet["Variable"] == "BOM_Forecast_Data_Future":
                    sheet["Errors"].append({"Code":407, "Description":error})
            return final_response
        else:
            return final_response



    def validate_all(self, forecast_dfs, forecast_sheets, usual_dfs, usual_sheets,input_data):
        """
        Validate all the dataframes and sheets
        """
        # Validation of forecast Sheets
        if len(forecast_sheets) >= 1:
            for df, sheet in zip(forecast_dfs, forecast_sheets):
                forecast_res = data_validator().validate_forecast_vals(df, input_data,sheet_name=sheet)
            forecast_response = SheetstoJSON().sheets_to_dict(forecast_res)
        else:
            forecast_response = {}

        # Validation of general sheets
        if len(usual_sheets) >= 1:
            for df,sheet in zip(usual_dfs, usual_sheets):
                regular_res = data_validator().validate_regular_file(df, input_data, sheet)
            regular_response = SheetstoJSON().sheets_to_dict(regular_res)
            if set(["Shipping_Interval", "Sourcing_Data", "Supply&Shipping_Var","Supply_Parameters", "Local_TT"]).issubset(set(usual_sheets)):
                temp_dict = dict(zip(usual_sheets, usual_dfs))
                Shipping_Interval = temp_dict.get('Shipping_Interval')
                Sourcing_Data = temp_dict.get('Sourcing_Data')
                Supply_Shipping_Var = temp_dict.get('Supply&Shipping_Var')
                Supply_Parameters = temp_dict.get('Supply_Parameters')
                local_tt = temp_dict.get('Local_TT')

                #Validate the RM Code and Supplier Code
                pairs_response = FileUtils().check_pairs(sourcing_data=Sourcing_Data, supply_and_shipping=Supply_Shipping_Var,
                                                        supply_parameter=Supply_Parameters, shipping_interval=Shipping_Interval, local_tt=local_tt)
                regular_response["Missing_RM_Supplier_Pairs"] = pairs_response.get('Base64')
                if pairs_response.get('Overall'):
                    overall = pairs_response.get('Overall')
                    for variable, status in overall.items():
                        if not status:
                            for response in regular_response["Sheets"]:
                                if response["Variable"] == variable:
                                    response["Errors"].append({"Code":409, "Description": "One or more RM codes and Supplier Codes pairs are missing in the input file. Please refer to Missing RM Codes Excel file"})
        else:
            regular_response = {}

        #Validate Only RM Code.
        dataframes =dict(zip(usual_sheets+forecast_sheets,usual_dfs+forecast_dfs))
        rm_validated_response = FileUtils().validate_rm_code(dataframes)
        regular_response["Missing_RM_Codes"] =  rm_validated_response.get('Base64')
        if rm_validated_response.get("Overall"):
            overall = rm_validated_response.get("Overall")
            for variable, status in overall.items():
                if not status:
                    for response in regular_response["Sheets"]:
                        if response["Variable"] == variable:
                            response["Errors"].append({"Code":410, "Description": "One or more RM codes are missing in the input file. Please refer to Missing RM Codes Excel file"})
        final_response = self.merge_response(forecast_response, regular_response)

        #validate the 12 month history and 6 month future data and add the error in forecast sheet.
        if len(forecast_dfs) == 2:
            history_future_error = validator_functions().validate_forecast_with_historical(forecast_dfs[0], forecast_dfs[1])
            updated_final_response = self.add_error_in_sheet(final_response,history_future_error)
        else:
            updated_final_response = final_response

        return updated_final_response