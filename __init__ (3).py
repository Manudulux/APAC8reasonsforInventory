import pandas as pd
from .demand_variation_utils import DemandVariationUtils
from src.helper import GLOBAL_CONFIG
import re

class DemandVariation:
    def __init__(self) -> None:
        self.load_config()

    def load_config(self):
        self.skewness = GLOBAL_CONFIG['global_parameters'][0]['forecast'].get('Skewness')
        self.demand_variation_method = GLOBAL_CONFIG['global_parameters'][0]['forecast'].get('demand_variation_method')
        self.maximum_percent_forecast = (GLOBAL_CONFIG['global_parameters'][0]['cappings'].get('Maximum Demand in % of Forecast'))

    import pandas as pd

    def merge_duplicate_rm_codes(self, df):
        """
        This function takes a DataFrame and merges rows with duplicate RM Codes by summing 
        the values of dynamic date columns (e.g., columns starting with '202').

        Parameters:
        - df (pd.DataFrame): The input DataFrame with duplicate RM Codes.

        Returns:
        - pd.DataFrame: The resulting DataFrame with merged RM Codes.
        """
        pattern = r'^\d{2}.?\d{4}$'
        sales_columns = [col for col in df.columns if re.match(pattern, str(col))]
        
        # Group by RM Code and aggregate
        df_grouped = df.groupby(['Plant Code','Plant Name', 'RM Code']).agg({
            'RM Name': 'first',     # Assuming RM Name is the same for each RM Code
            'Category': 'first',    # Assuming Category is the same for each RM Code
            'Source': 'first',      # Assuming Source is the same for each RM Code
            'Cycle': 'first',       # Same assumption for Cycle
            **{col: 'sum' for col in sales_columns}  # Sum the dynamic date columns
        }).reset_index()
        
        return df_grouped


    def calculate_demand_variation(self,plant_code, rm_code, dataframes:dict) -> dict:
        # Step 1: Fetch Consumption DF
        consumption_df = dataframes["Consumption_Invoice_Hist"]
        # Step 3: Fetch 12 Month Forecast DF
        forecast_df = dataframes["BOM_Forecast_Data_History"]
        future_df = dataframes["BOM_Forecast_Data_Future"]
        future_df = self.merge_duplicate_rm_codes(future_df)
        forecast_df = self.merge_duplicate_rm_codes(forecast_df)

        # Get the columns for 6m_forecast (everything except the common columns)
        forecast_columns_6m = [col for col in future_df.columns if col not in ['Plant Name', 'Plant Code', 'RM Code', 'RM Name', 'Category', 'Source', 'Cycle']]

        # Merge forecast_df with future_df based on common columns: 'Plant Code', 'RM Code', and 'Cycle'
        forecast_df = pd.merge(
            forecast_df,
            future_df[['Plant Code', 'RM Code', 'Cycle'] + forecast_columns_6m],  # Select the relevant columns for the 6-month forecast
            on=['Plant Code', 'RM Code', 'Cycle'],
            how='left'  # Use a left join to keep all rows from the forecast_df
        )
        forecast_df.fillna(0, inplace=True)
        rm_consumption_df = consumption_df[(consumption_df["RM Code"]==rm_code) & (consumption_df["Plant Code"]==plant_code)]
        # Step 4: Fetch Week Month Year Data from Post Date and Post Week
        wmy_consumption_df = DemandVariationUtils().fetch_month_week_year(rm_consumption_df)
        # Step 5: Merge Week and Sort Month, Week, Year and Movement Order Quantity
        sorted_consumption_df = DemandVariationUtils().fetch_sorted_consumption_df(wmy_consumption_df)
        # Step 6: Fetch Forecast Data for Particular RM Code
        forecast_df_rm_code = forecast_df[(forecast_df["RM Code"]==rm_code) & (forecast_df["Plant Code"]==plant_code)]
        # forecast_df_rm_code is null
        if forecast_df_rm_code.empty:
            return None
        # Step 7: Fetch Forecast Value
        fcast_cons_df = DemandVariationUtils().add_forecast_col(sorted_consumption_df, forecast_df_rm_code)
        fcast_cons_df['Movement Qty'] = fcast_cons_df['Movement Qty']*-1
        # Step 8: Checking Skewness Global Parameter
        if self.skewness:
            # Calculation With Skewness
            final_output = DemandVariationUtils().with_skewness_calc(fcast_cons_df)
        else:
            # Calculation Without Skewness
            final_output = DemandVariationUtils().without_skewness_calc(fcast_cons_df)
        # Step 9: Checking Demand Variation Global Parameter
        if self.demand_variation_method=="Under":
            final_output = DemandVariationUtils().removing_less_than_0_val(final_output)
        if self.maximum_percent_forecast is None:
            weekly_rmse = DemandVariationUtils().calculate_weekly_rmse(final_output)
        else:
            # Step 10: Calculating % to forecast column
            final_output = DemandVariationUtils().add_percent_to_forecast(final_output)

            # Step 11: Calculating revised actual consumption
            final_output = DemandVariationUtils().revised_actual_consumption(final_output)

            # Step 12: Calculating New Over Consumption
            final_output = DemandVariationUtils().new_over_consumption(final_output)

            weekly_rmse = DemandVariationUtils().calculate_weekly_rmse(final_output)
        return weekly_rmse
