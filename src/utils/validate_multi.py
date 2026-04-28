import base64
from io import BytesIO
from src.helper import FILES, convert_df_to_base64
from src.helper.J2S import JSONtoSheets
from src.helper.utils import FileUtils
from src.helper.validations import Validatator
from src.helper.ValidateSheets import Validation
from src.component.utils import CalculationUtility


class data_validation:
    def __init__(self) -> None:
        pass

    def upload_multi_excel(self, input_data):
        try:
            input_obj_list = JSONtoSheets().ConvertJSONToSheets(input_data)
            dataframes = FileUtils().process_multi_excel(input_obj_list)
            if isinstance(dataframes, dict):
                pass
            else:
                return {"error": dataframes}, 400
            if ("SKU_Transition" in dataframes.keys()) and ("Supplier_Transition" in dataframes.keys()):
                dataframes = CalculationUtility().code_transition(dataframes)
            if len(dataframes) == 12:
                dataframes = CalculationUtility().filtered_dataframes(dataframes, True)

            forecast_dfs, other_dfs, valid_forecast_sheets, valid_others_sheets = [], [], [], []
            for sheets in FILES['forecast_sheets']:
                df = dataframes.get(sheets)
                if df is not None and not df.empty:
                    forecast_dfs.append(df)
                    valid_forecast_sheets.append(sheets)
            for sheets in FILES['other_sheets']:
                df = dataframes.get(sheets)
                if df is not None and not df.empty:
                    other_dfs.append(df)
                    valid_others_sheets.append(sheets)

            pre_response = Validatator().validate_all(forecast_dfs, valid_forecast_sheets, other_dfs, valid_others_sheets, input_obj_list)
            return pre_response
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}


class IntermediateFile:
    def __init__(self, validated_data) -> None:
        self.validated_data = validated_data

    def make_response(self, intermediate_output):
        updated_sheets = []
        intermediate_template = ["Sourcing_Data", "Supply_Parameters"]
        for sheet in self.validated_data["Sheets"]:
            for name in intermediate_output.keys():
                if name in intermediate_template and sheet["Variable"] == name:
                    sheet["Columns"] = []
                    # No template files on Streamlit Cloud — just encode directly
                    sheet["Data"] = convert_df_to_base64(intermediate_output[name])
                    updated_sheets.append(sheet)
                elif name in sheet["Variable"]:
                    sheet["Columns"] = []
                    updated_sheets.append(sheet)

        rm_seg_b64 = ""
        rm_seg = intermediate_output.get('RM_Segmentation_Output')
        if rm_seg is not None and hasattr(rm_seg, 'shape') and rm_seg.shape[0] > 0:
            rm_seg_b64 = convert_df_to_base64(rm_seg)

        return {"Sheets": updated_sheets, "RM_Segmentation_Output": rm_seg_b64}
