from src.helper.J2S import JSONtoSheets
from src.helper.utils import FileUtils
from src.component.utils import CalculationUtility
from src.component.sourcing_formulas import SourcingCalculations
from src.component.supply_formulas import SupplyParameter

class GenerateIntermediateOutput:
    def __init__(self, input_data ) -> None:
        self.input_data = input_data

    def json_to_dataframes(self):
        validated_input = JSONtoSheets().ConvertJSONToSheets(self.input_data)
        dataframes = FileUtils().process_multi_excel(validated_input)
        if isinstance(dataframes, dict):
                pass
        else:
            return {"error":dataframes}, 400
        
        if ("SKU_Transition" in dataframes.keys()) and ("Supplier_Transition" in dataframes.keys()):
            if "Supply_Parameters" in dataframes.keys():
                dataframes = CalculationUtility().delete_old_sku_supply_parameter(dataframes)
            dataframes = CalculationUtility().code_transition(dataframes)
        if ('Actual_Inventory' in dataframes.keys()):
            act_inventory = dataframes.get('Actual_Inventory')
            act_inventory = act_inventory.groupby(['CODE', 'Plant Code'], as_index=False).agg({'QTY': 'sum','MAP': 'sum','VALUE': 'sum'})
            dataframes['Actual_Inventory'] = act_inventory
        if ("Consumption_Invoice_Hist" in dataframes.keys()) and ("Product_Master" in dataframes.keys()):
            dataframes = CalculationUtility().rm_name_transition(dataframes)
        if len(dataframes) == 12:
            dataframes = CalculationUtility().remove_0_sob(dataframes=dataframes)
            dataframes = CalculationUtility().filtered_dataframes(dataframes, False)
        return dataframes

    def handle_transition(self):
        dataframes = self.json_to_dataframes()
        updated_dfs = CalculationUtility().code_transition(dataframes)
        return updated_dfs

    def handle_historical(self):
        transition_response = self.handle_transition()
        dataframes= CalculationUtility().filter_historical(transition_response)
        return dataframes

    def calculate_supply_parameters_data(self):
        dataframes = self.handle_historical()
        supply_response = SupplyParameter(dataframes).Calculate()
        return supply_response

    def calculate_sourcing_data(self):
        updated_df = self.calculate_supply_parameters_data()
        calculated_dfs = SourcingCalculations().final_sourcing_df(updated_df)
        return calculated_dfs

    def generate_intermediate_response(self):
        intermediate_response = self.calculate_sourcing_data()
        intermediate_response = CalculationUtility().add_default_data(intermediate_response)
        return intermediate_response
