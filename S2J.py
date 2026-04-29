"""Supportive utils file"""
from io import BytesIO
import os, base64, io
from typing import Union, Dict
from src.helper.data_validator import data_validator
import pandas as pd
from src.helper import VALIDATION_CONFIG, add_data_to_excel_with_formatting
from src.helper.S2J import SheetstoJSON

class FileUtils:

    def excel_parcer(self, file):
        return pd.read_excel(file)

    def decode_and_read_excel(self, base64_str, file_key):
        try:
            decoded_file = base64.b64decode(base64_str)
            excel_data = io.BytesIO(decoded_file)
            df = pd.read_excel(excel_data, sheet_name=None)
            return df
        except Exception as e:
            raise ValueError(f"Error reading {file_key} file: {str(e)}")

    def read_template(self, input_file):
        excel_file = pd.ExcelFile(BytesIO(input_file))
        sheet_names = excel_file.sheet_names
        return excel_file, sheet_names

    def process_multi_excel(self, input_file_data):
        try:
            file_data = [{cd.Variable: cd.Data} for cd in input_file_data]
            single_json = {}
            for item in file_data:
                single_json.update(item)
            dataframes = {}
            for key, value in single_json.items():
                if value:
                    decoded_file = base64.b64decode(value)
                    excel_data = io.BytesIO(decoded_file)
                    df = pd.read_excel(excel_data, sheet_name=None)
                    sheet_name = next(iter(df.keys()))
                    dataframes.update({key: df[sheet_name]})
            return dataframes
        except Exception as e:
            return f"An error occurred: {str(e)}"

    def process_single_excel_file(self, excel_file, sheet_names: list) -> Union[str, Dict[str, pd.DataFrame]]:
        try:
            required_sheets = [x["Name"] for x in VALIDATION_CONFIG["Sheets"]] if isinstance(VALIDATION_CONFIG, dict) else [x.Name for x in VALIDATION_CONFIG]
            missing_sheets = [sheet for sheet in required_sheets if sheet not in sheet_names]
            if missing_sheets:
                return f"The following sheets are missing: {', '.join(missing_sheets)}. Please reupload the file."
            dataframes = []
            form_sheet = []
            for sheet in required_sheets:
                formatted_sheet_name = sheet.replace(" ", "_").replace("(", "").replace(")", "")
                form_sheet.append(formatted_sheet_name)
                df = pd.read_excel(excel_file, sheet_name=sheet)
                dataframes.append(df)
            return dict(zip(form_sheet, dataframes))
        except Exception as e:
            return f"An error occurred: {str(e)}"

    def check_pairs(self, sourcing_data, supply_parameter, supply_and_shipping, shipping_interval, local_tt):
        try:
            rm_code_columns = ['RM Code', 'Material Code', 'CODE']
            supplier_code_columns = ['Supplier Code', 'Supplier']
            plant_code_columns = ['Plant Code']
            supply_parameter['Supplier Code'] = supply_parameter['Supplier Code'].astype(int)
            sourcing_data['RM Code'] = sourcing_data['RM Code'].astype(int)
            supplier_mapping = dict(zip(supply_parameter['Supplier Code'], supply_parameter['Supplier Name']))
            rm_mapping = dict(zip(supply_parameter["Material Code"], supply_parameter["Material Desc"]))

            def extract_pairs(df, rm_col_options, supplier_col_options, plant_col_options):
                rm_col = next((col for col in rm_col_options if col in df.columns), None)
                supplier_col = next((col for col in supplier_col_options if col in df.columns), None)
                plant_col = next((col for col in plant_col_options if col in df.columns), None)
                if not rm_col or not supplier_col or not plant_col:
                    return None, None, None, f"Missing columns"
                return set(zip(df[plant_col], df[rm_col], df[supplier_col])), rm_col, supplier_col, plant_col

            sourcing_pairs, *_ = extract_pairs(sourcing_data, rm_code_columns, supplier_code_columns, plant_code_columns)
            supply_parameter_pairs, *_ = extract_pairs(supply_parameter, rm_code_columns, supplier_code_columns, plant_code_columns)
            all_pairs = sourcing_pairs | supply_parameter_pairs
            report = []
            for plant, rm_code, supplier_code in all_pairs:
                in_sourcing = (plant, rm_code, supplier_code) in sourcing_pairs
                in_supply_parameter = (plant, rm_code, supplier_code) in supply_parameter_pairs
                if not (in_sourcing and in_supply_parameter):
                    report.append({
                        "Plant Code": plant, "RM Code": rm_code, "Supplier Code": supplier_code,
                        "In Sourcing Data": in_sourcing, "In Supply Parameter": in_supply_parameter,
                    })
            overall = {
                "Sourcing_Data": all(e["In Sourcing Data"] for e in report),
                "Supply_Parameters": all(e["In Supply Parameter"] for e in report),
            }
            base64_encoded = ""
            if len(report) > 0:
                report_df = pd.DataFrame(report)
                report_df['Supplier Name'] = report_df['Supplier Code'].map(supplier_mapping)
                report_df['RM Desc'] = report_df['RM Code'].map(rm_mapping)
                output = BytesIO()
                report_df.to_excel(output, index=False)
                output.seek(0)
                base64_encoded = base64.b64encode(output.read()).decode('utf-8')
            return {"Report": report, "Overall": overall, "Errors": [], "Base64": base64_encoded}
        except Exception as e:
            return f"An error occurred: {str(e)}"

    def validate_rm_code(self, dataframes):
        try:
            report = []
            base_rm_plant_pair = dataframes["BOM_Forecast_Data_Future"].apply(lambda row: (row['RM Code'], row['Plant Code']), axis=1).to_list()
            supply_param_rm_plant_pair = dataframes["Supply_Parameters"].apply(lambda row: (row['Material Code'], row['Plant Code']), axis=1).to_list()
            sourcing_rm_plant_pair = dataframes["Sourcing_Data"].apply(lambda row: (row['RM Code'], row['Plant Code']), axis=1).to_list()
            shipping_rm_plant_pair = dataframes["Shipping_Interval"].apply(lambda row: (row['RM Code'], row['Plant Code']), axis=1).to_list()
            supply_rm_plant_pair = dataframes["Supply&Shipping_Var"].apply(lambda row: (row['Material Code'], row['Plant Code']), axis=1).to_list()
            consumption_rm_plant_pair = dataframes["Consumption_Invoice_Hist"].apply(lambda row: (row['RM Code'], row['Plant Code']), axis=1).to_list()
            history_rm_plant_pair = dataframes["BOM_Forecast_Data_History"].apply(lambda row: (row['RM Code'], row['Plant Code']), axis=1).to_list()
            act_inventory_rm_plant_pair = dataframes["Actual_Inventory"].apply(lambda row: (row['CODE'], row['Plant Code']), axis=1).to_list()
            product_master_rm_code = dataframes["Product_Master"]['SKU'].to_list()
            local_tt_rm_plant_pair = dataframes["Local_TT"].apply(lambda row: (row['CODE'], row['Plant Code']), axis=1).to_list()
            rm_mapping = dict(zip(dataframes["BOM_Forecast_Data_Future"]['RM Code'], dataframes["BOM_Forecast_Data_Future"]['RM Name']))
            validation_results = {
                "Sourcing_Data": all(pair in sourcing_rm_plant_pair for pair in base_rm_plant_pair),
                "Shipping_Interval": all(pair in shipping_rm_plant_pair for pair in base_rm_plant_pair),
                "Supply_Shipping_Var": False,
                "Consumption_Invoice_Hist": all(pair in consumption_rm_plant_pair for pair in base_rm_plant_pair),
                "Supply_Parameters": all(pair in supply_param_rm_plant_pair for pair in base_rm_plant_pair),
                "BOM_Forecast_Data_History": all(pair in history_rm_plant_pair for pair in base_rm_plant_pair),
                "Actual_Inventory": all(pair in act_inventory_rm_plant_pair for pair in base_rm_plant_pair),
                "Product_Master": all(rm_code in product_master_rm_code for rm_code, _ in base_rm_plant_pair),
                "Local_TT": False
            }
            for pair in base_rm_plant_pair:
                if pair in supply_rm_plant_pair or pair in local_tt_rm_plant_pair or pair in shipping_rm_plant_pair:
                    validation_results["Supply&Shipping_Var"] = True
                    validation_results["Local_TT"] = True
                    validation_results["Shipping_Interval"] = True
            for rm_code, plant_code in base_rm_plant_pair:
                report_data = {
                    "RM Code": rm_code, "Plant Code": plant_code,
                    "Sourcing_Data": (rm_code, plant_code) in sourcing_rm_plant_pair,
                    "Shipping_Interval": (rm_code, plant_code) in shipping_rm_plant_pair,
                    "Supply_Shipping_Var": (rm_code, plant_code) in supply_rm_plant_pair,
                    "Consumption_Invoice_Hist": (rm_code, plant_code) in consumption_rm_plant_pair,
                    "Supply_Parameters": (rm_code, plant_code) in supply_param_rm_plant_pair,
                    "BOM_Forecast_Data_History": (rm_code, plant_code) in history_rm_plant_pair,
                    "Actual_Inventory": (rm_code, plant_code) in act_inventory_rm_plant_pair,
                    "Product_Master": rm_code in product_master_rm_code,
                    "Local TT": (rm_code, plant_code) in local_tt_rm_plant_pair
                }
                all_true = all(report_data[key] for key in report_data if key not in ["RM Code", "Plant Code", "Local TT", "Supply_Shipping_Var"])
                all_false = not any(report_data[key] for key in report_data if key not in ["RM Code", "Plant Code"])
                any_other_false = any(report_data[key] is False for key in report_data if key not in ["RM Code", "Plant Code", "Local TT", "Supply_Shipping_Var"])
                if all_false or any_other_false:
                    report.append(report_data)
                if all_true and not report_data["Local TT"] and not report_data["Supply_Shipping_Var"]:
                    report.append(report_data)
            base64_encoded = ""
            if len(report) > 0:
                report_df = pd.DataFrame(report)
                report_df["RM Desc"] = report_df["RM Code"].map(rm_mapping)
                output = BytesIO()
                report_df.to_excel(output, index=False)
                output.seek(0)
                base64_encoded = base64.b64encode(output.read()).decode('utf-8')
            return {"Report": report, "Overall": validation_results, "Base64": base64_encoded}
        except Exception as e:
            return {"Report": None, "Overall": None, "Error": str(e)}

    def validation_intermediate(self, input_obj_list):
        try:
            dataframes = self.process_multi_excel(input_obj_list)
            old_rm_codes = dataframes["SKU_Transition"]["Phase-Out RM Code"].unique().tolist()
            old_supplier_codes = dataframes["Supplier_Transition"]["Phase-Out Supplier Code"].unique().tolist()
            sourcing_data = dataframes["Sourcing_Data"]
            supply_parameter = dataframes["Supply_Parameters"]
            sheet_names = ["Sourcing_Data", "Supply_Parameters"]
            sheets_df = [sourcing_data, supply_parameter]
            for df, sheet in zip(sheets_df, sheet_names):
                regular_res = data_validator().validate_intermediate_file(df, input_obj_list, sheet, old_supplier_codes, old_rm_codes)
            response = SheetstoJSON().sheets_to_dict(regular_res)
            return response
        except Exception as e:
            return f"An error occurred: {str(e)}"
