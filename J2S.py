import pandas as pd
from src.helper.validation_helper import validator_functions

class data_validator:

    def validate_regular_file(self, df: pd.DataFrame, input_data, sheet_name: str) -> dict:
        try:
            """
            Validates the columns in the DataFrame based on the JSON rules provided.
            Returns validation errors or success message in a specified format.
            """
            validation_rules = validator_functions().find_rules(sheet_name)
            for sheet in input_data:
                if sheet.Variable in sheet_name:
                    sheet.Errors= [{"Code":401, "Description": validator_functions().validate_missing_columns(df, validation_rules)},
                    {"Code":402, "Description":validator_functions().validate_null_values(df, validation_rules)},
                    {"Code":403, "Description":validator_functions().validate_data_types(df, validation_rules)},
                    {"Code":404, "Description":validator_functions().validate_data_expression(df, validation_rules)},
                    {"Code":405, "Description":validator_functions().validate_repeat_number(df, validation_rules)}]
                    sheet.Errors = list(filter(lambda x: x.get("Description") != [], sheet.Errors))
            return input_data
        except Exception as e:
            return f"An error occurred: {str(e)}"

    def validate_forecast_vals(self, df: pd.DataFrame,input_data, sheet_name: str) -> dict:
        try:
            """
            Validates forecast columns in the DataFrame based on the rules provided.
            Returns validation errors or success message in a specified format.
            """
            find_rule_obj = validator_functions()
            validation_rules = find_rule_obj.find_rules(sheet_name)
            df.columns = df.columns.map(str)

            #Add the error in sheet obj.
            for sheet in input_data:
                if sheet.Variable in sheet_name and sheet.Data != "":
                    sheet.Errors=[
                                    {"Code":401, "Description":validator_functions().validate_missing_columns(df, validation_rules)},
                                    {"Code":402, "Description":validator_functions().validate_null_values(df, validation_rules)},
                                    {"Code":403, "Description":validator_functions().validate_data_types(df, validation_rules)},
                                    {"Code":404, "Description":validator_functions().validate_data_expression(df, validation_rules)},
                                    {"Code":405, "Description":validator_functions().validate_repeat_number(df, validation_rules)},
                                    {"Code":406, "Description":validator_functions().validate_sequence(df, validation_rules)},
                                    {"Code":407, "Description":validator_functions().validate_forecast_columns(df, validation_rules)}]
                    sheet.Errors = list(filter(lambda x: x.get("Description") != [], sheet.Errors))
            return input_data
        except Exception as e:
            return f"Error in Validate Forecast Cols - , {e}"
        
    def validate_old_codes(self, df: pd.DataFrame, old_supplier_codes: list, old_rm_codes: list) -> list:
        """Check if any old RM codes or old supplier codes are present in the DataFrame."""
        try:
            errors = []
            
            # Define possible column names for RM and Supplier codes
            RM_CODES = ["RM CODE", "SKU", "Material Code", "RM Code", "CODE"]
            SUPPLIER_CODES = ["Supplier Code", "Supplier"]

            # Check for old RM codes in relevant columns
            for rm_column in RM_CODES:
                if rm_column in df.columns:
                    # Check if any of the old RM codes are in the column
                    found_rm_codes = df[rm_column].isin(old_rm_codes)
                    if found_rm_codes.any():
                        errors.append("Old RM Codes found in the file. Please check and reupload")

            # Check for old Supplier codes in relevant columns
            for supplier_column in SUPPLIER_CODES:
                if supplier_column in df.columns:
                    # Check if any of the old Supplier codes are in the column
                    found_supplier_codes = df[supplier_column].isin(old_supplier_codes)
                    if found_supplier_codes.any():
                        errors.append("Old Supplier Codes found in the file. Please check and reupload")

            return errors
        
        except Exception as e:
            return [f"Error in function: validate_old_codes: {e}"]
        
    def validate_intermediate_file(self, df: pd.DataFrame, input_data, sheet_name: str,old_supplier_codes:list, old_rm_codes: list ) -> dict:
        try:
            """
            Validates the columns in the DataFrame based on the JSON rules provided.
            Returns validation errors or success message in a specified format.
            """
            validation_rules = validator_functions().find_intermediate_rules(sheet_name)
            for sheet in input_data:
                if sheet.Variable in sheet_name:
                    sheet.Errors= [{"Code":401, "Description": validator_functions().validate_missing_columns(df, validation_rules)},
                    {"Code":402, "Description":validator_functions().validate_null_values(df, validation_rules)},
                    {"Code":403, "Description":validator_functions().validate_data_types(df, validation_rules)},
                    {"Code":404, "Description":validator_functions().validate_data_expression(df, validation_rules)},
                    {"Code":405, "Description":validator_functions().validate_repeat_number(df, validation_rules)},
                    # {"Code":406, "Description":data_validator().validate_old_codes(df, old_supplier_codes, old_rm_codes)}
                    ]
                    sheet.Errors = list(filter(lambda x: x.get("Description") != [], sheet.Errors))
            return input_data
        except Exception as e:
            return f"An error occurred: {str(e)}"