import numpy as np
import pandas as pd
import math
from src.helper.utils import FileUtils
from src.helper.S2J import SheetstoJSON
from src.helper import GLOBAL_CONFIG, convert_df_to_base64
from ..final_output.avg_daily_sales import  DailySalesUtils
from ..final_output.demand_variation import DemandVariation
from ..final_output.final_calculation import FinalCalculation
from src.component.utils import CalculationUtility
from datetime import datetime
from src.final_output.utils import generate_output_dataframes, generate_encoded_output

# # simple debug logger — prints reliably inside .exe
# def debug_log(*args):
#     print("[DEBUG]", *args, flush=True)


class EightReasons:
    def __init__(self,intermediate_input,rm_df) -> None:
        #convert the input json obj to dataframe and dict obj.
        self.final_response = SheetstoJSON().sheets_to_dict(intermediate_input)
        self.final_response["Final_Output"] = ""
        self.final_response["Consumption_merged"] = ""
        self.final_response["RM_Seg_merged"] = ""
        self.dataframes = FileUtils().process_multi_excel(intermediate_input)
        self.dataframes = self.preprocess(self.dataframes)
        self.dataframes['rm_segmentation_output'] = rm_df
        self.dataframes = self.generate_final_consumption(self.dataframes)
        self.dataframes = self.generate_final_rm_segmentation(self.dataframes)
        self.load_config()
    
    def load_config(self):
        self.cycle_stock_cm = GLOBAL_CONFIG['global_parameters'][0]['cycle_stock'].get('calculation_methodology')
        self.saftey_cap = GLOBAL_CONFIG['global_parameters'][0]['cappings'].get('safety_stock_cap')
        self.shipping_interval_cap = GLOBAL_CONFIG['global_parameters'][0]['cappings'].get('shipping_interval_cap')
        self.maximum_percent_forecast = GLOBAL_CONFIG['global_parameters'][0]['cappings'].get('Maximum Demand in % of Forecast')
        self.transit_cap = GLOBAL_CONFIG['global_parameters'][0]['cappings'].get('transit_time_cap')
        self.production_days = sum(GLOBAL_CONFIG['global_parameters'][0]['production_days'].values())
        self.USD_value = GLOBAL_CONFIG['global_parameters'][0]['price_conversion']['USD_value']

    def preprocess(self, dataframes):
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
    
    def generate_final_consumption(self, dataframes):
        try:
            supply_parameter = dataframes["Supply_Parameters"].copy()
            consumption = dataframes['Consumption_Invoice_Hist'].copy()
            product_master = dataframes['Product_Master'].copy()
            rm_segmentation = dataframes['rm_segmentation_output'].copy()

            merged_df = pd.merge(consumption, product_master[['SKU', 'Planning cycle', 'RM Class Group', 'SKU Description']], 
                        left_on='RM Code', right_on='SKU', how='left')

            # Drop the redundant 'SKU' column after merge
            merged_df = merged_df.drop(columns=['SKU', 'RM Name'])
            merged_df.rename(columns={'SKU Description': 'RM Name'}, inplace=True)

            supply_parameter.rename(columns={'Material Code':'RM Code'}, inplace=True)
            consumption_final_df = pd.merge(merged_df, supply_parameter[['Region', 'Plant Code', 'RM Code', 'INCO Term', 'Source Country', 'Source Region', 'RM Type', 'SOB']],
                        left_on=['Plant Code', 'RM Code'], right_on=['Plant Code', 'RM Code'], how='left')
            
            # Multiplying the Movement QTY with SOB
            consumption_final_df['Movement Qty'] = consumption_final_df['Movement Qty'] * consumption_final_df['SOB']
            consumption_final_df.rename(columns={'RM Type':'Category'}, inplace=True)
            final_df = pd.merge(consumption_final_df, rm_segmentation[['RM Code', 'Plant Code', 'Segmentation', 'MAP']],
                        left_on=['Plant Code', 'RM Code'], right_on=['Plant Code', 'RM Code'],
                        how='left'
                        )
            supply_parameter.rename(columns={'RM Code' : 'Material Code'}, inplace=True)
            dataframes['Consumption_merged'] = final_df
            return dataframes
        except Exception as e:
            import traceback; traceback.print_exc()
            raise RuntimeError(f"generate_final_consumption failed: {e}") from e

    def generate_final_rm_segmentation(self, dataframes):
        try:
            supply_parameter = dataframes["Supply_Parameters"]
            product_master = dataframes['Product_Master']
            rm_segmentation = dataframes['rm_segmentation_output']

            merged_df = pd.merge(rm_segmentation, product_master[['SKU', 'Planning cycle', 'RM Class Group', 'SKU Description']], 
                     left_on='RM Code', right_on='SKU', how='left')

            # Drop the redundant 'SKU' column after merge
            merged_df = merged_df.drop(columns=['SKU', 'RM Name'])
            merged_df.rename(columns={'SKU Description': 'RM Name'}, inplace=True)

            supply_parameter.rename(columns={'Material Code':'RM Code'}, inplace=True)
            ## Fetch the indexes of  the RMs with highest SOB
            max_sob_idx = supply_parameter.groupby(
                        ['Region', 'PLANT', 'Plant Code', 'RM Code', 'Material Desc']
                    )['SOB'].idxmax()

            filtered_supply = supply_parameter.loc[max_sob_idx]

            rm_seg_final_df = pd.merge(merged_df, filtered_supply[['Region', 'Plant Code', 'RM Code', 'INCO Term', 'Source Country', 'Source Region', 'RM Type']],
                     left_on=['Plant Code', 'RM Code'], right_on=['Plant Code', 'RM Code'], how='left')
            rm_seg_final_df.rename(columns={'RM Type':'Category'}, inplace=True)

            supply_parameter.rename(columns={'RM Code' : 'Material Code'}, inplace=True)
            rm_seg_final_df.drop_duplicates(inplace=True)
            dataframes['RM_Seg_merged'] = rm_seg_final_df
            return dataframes
        except Exception as e:
            import traceback; traceback.print_exc()
            raise RuntimeError(f"generate_final_rm_segmentation failed: {e}") from e

    def calculate_data_quality(self, df, exclude_columns):
        """
        Calculate data quality score for each row based on missing or zero values.
        A row with no missing or zero values will have a score of 100%.
        """
        target_columns = [col for col in df.columns if col not in exclude_columns]

        def row_data_quality(row):

            missing_or_zero = (row[target_columns].isnull()) | (row[target_columns] == 0)
            missing_count = missing_or_zero.sum()
            
            total_columns = len(target_columns)
            data_quality = (1 - missing_count / total_columns) * 100
            
            return str(math.ceil(data_quality)) + '%'
        
        df['Historical Data Quality'] = df.apply(row_data_quality, axis=1)  
        return df
    
    def calculate_undermin_overmax(self, final_output):
        try:
            act_inventory = self.dataframes['Actual_Inventory'].copy()
            final_output["New 8 reasons"] = final_output["8 Reasons (DSI)"] - final_output["Transit (DSI)"]
            act_inventory.rename(columns={'CODE': 'Material Code'}, inplace=True)
            merged_df = pd.merge(final_output, act_inventory[['Material Code','Plant Code', 'QTY']], 
                     left_on=['Material Code', 'Plant Code'],
                     right_on=['Material Code', 'Plant Code'],
                     how='left')
            act_inventory.rename(columns={'Material Code' : 'CODE'}, inplace=True)
            merged_df["Actual Inv Days Cover"] = np.where(merged_df["Average Daily Sales (Future)"] == 0, 0,  merged_df["QTY"] / merged_df["Average Daily Sales (Future)"])
            merged_df['pre-under Min'] = merged_df['Min (DSI)'] - merged_df["Actual Inv Days Cover"]
            merged_df['pre-under Min'] = merged_df['pre-under Min'].apply(lambda x: max(x, 0))
            merged_df['pre-over max'] = merged_df['Max (DSI)'] - merged_df["Actual Inv Days Cover"]
            merged_df['pre-over max'] = merged_df['pre-over max'].apply(lambda x: 0 if x > 0 else x)
            merged_df['under min qty'] = merged_df['pre-under Min'] * merged_df['Average Daily Sales (Future)']
            merged_df['over max qty'] = merged_df['pre-over max'] * merged_df['Average Daily Sales (Future)']
            merged_df['Under Min (Val)'] = merged_df['under min qty'] * merged_df['MAP'] / self.USD_value / 10**6
            merged_df['Over Max (Val)'] = merged_df['over max qty'] * merged_df['MAP'] / self.USD_value / 10**6
            merged_df.drop(columns=['New 8 reasons', 'QTY', 'Actual Inv Days Cover', 'pre-under Min', 'pre-over max',
                                    'under min qty', 'over max qty'], inplace=True)
            return merged_df

        except Exception as e:
            return e


    def calculate(self):
        # try:
            #make final output dataframe after final calculation.
            final_output_df = FinalCalculation(self.dataframes).initiate()
            #-----------------------------------------------------------------#
            #----------------------------R1-R8-Calculation--------------------------#
            #-----------------------------------------------------------------#

            #Calculate R1 Information Cycle (DSI)
            final_output_df["R1 Information Cycle (DSI)"] = round(final_output_df["Review Period (days)"].apply(lambda x:x*0.5), 2)

            # Adding Capping to the R1 Information Cycle (DSI) -- 19/12/2024
            if self.shipping_interval_cap is not None:
                final_output_df['R1 Information Cycle (DSI)'] = np.where(
                    final_output_df['R1 Information Cycle (DSI)'] > self.shipping_interval_cap, 
                    self.shipping_interval_cap, 
                    final_output_df['R1 Information Cycle (DSI)']
                )
            #Calculate R2 Manufacturing Lot Size (DSI)
            final_output_df["Average Daily Sales"] = final_output_df["Average Daily Sales"] = final_output_df.apply(lambda row: DailySalesUtils().fetch_month_week_year(row["Material Code"], row["Plant Code"], self.dataframes["Consumption_Invoice_Hist"]),axis=1)

            final_output_df["Average Daily Sales"] = (final_output_df["Average Daily Sales"].fillna(0) * final_output_df["SOB"])

            # final_output_df["R2 Manufacturing Lot Size (DSI)"] = round(final_output_df.apply(lambda x:(x["MINIMUM ORDER QTY (Units)"]/(x["Average Daily Sales"]))*0.5,axis=1), 2)
            final_output_df["R2 Manufacturing Lot Size (DSI)"] = (final_output_df.apply(lambda x: 0 if x["Average Daily Sales"] == 0 else (x["MINIMUM ORDER QTY (Units)"] / x["Average Daily Sales"]) * 0.5,axis=1).round(2))
            #Calculate R3 Shipping Lot Size (DSI)
            final_output_df["R3 Shipping Lot Size (DSI)"] = round(final_output_df.apply(lambda x: 0 if x["Average Daily Sales"]==0 else (x["Shipping Lot Size (Units)"]/(x["Average Daily Sales"]))*0.5,axis=1), 2)
            #Calculate R4 Shipping Interval (DSI)
            final_output_df["R4 Shipping Interval (DSI)"] = round(final_output_df['Shipping Interval (Days)'].apply(lambda x:x*0.5), 2)
            #Adding Capping for the R4 Shipping Interval (DSI)
            if self.shipping_interval_cap is not None:
                final_output_df['R4 Shipping Interval (DSI)'] = np.where(
                    final_output_df['R4 Shipping Interval (DSI)'] > self.shipping_interval_cap, 
                    self.shipping_interval_cap, 
                    final_output_df['R4 Shipping Interval (DSI)']
                )  
            #Calculate R5 Geography (DSI)
            final_output_df["R5 Geography (DSI)"] = round(final_output_df['Lead Time (days)'].apply(lambda x:x), 2)
            #Calculate R6 Shipping Variation (DSI)
            final_output_df["R6 Shipping Variation (DSI)"] = round(final_output_df.apply(lambda x:((x['Transit Time Std. Dev. (%)']/100)*x['Lead Time (days)'])*x['Service Level Factor (z)'],axis=1), 2)
            #Calculate R7 Supply Variation (DSI)
            final_output_df["R7 Supply Variation (DSI)"] = round(final_output_df.apply(lambda x:((1-(x['Supply Reliability (%)']/100)))*x['Service Level Factor (z)']*np.sqrt(x['Risk-Horizon (days)']),axis=1), 2)
            #Calculate R8 Demand Variation (DSI)
            final_output_df["Weekly RMSE"] = round(final_output_df.apply(
                lambda row: DemandVariation().calculate_demand_variation(row['Plant Code'], row["Material Code"], self.dataframes), axis=1
            ), 3)
            # final_output_df["R8 Demand Variation (DSI)"] = round(final_output_df.apply(
            #     lambda row: ((row["Weekly RMSE"]*np.sqrt(row['Risk-Horizon (days)']/7)*row['Service Level Factor (z)'])/(row["Average Daily Sales"])), axis=1
            # ), 3)

            final_output_df["R8 Demand Variation (DSI)"] = final_output_df.apply(lambda r: (0 if r["Average Daily Sales"] == 0 else (r["Weekly RMSE"] * np.sqrt(r["Risk-Horizon (days)"] / 7) * r["Service Level Factor (z)"]) / r["Average Daily Sales"]),axis=1).round(3)

            # Calculate average daily sales (future)
            future_forecast = self.dataframes.get('BOM_Forecast_Data_Future')
            future_forecast = DailySalesUtils().total_sales_forecast(future_forecast)
            # future_forecast["Average_Daily_Sales"] = future_forecast['Total_RM_Sales']/self.production_days
            future_forecast["Average_Daily_Sales"] = (future_forecast["Total_RM_Sales"] / self.production_days if self.production_days != 0 else 0)
            rm_daily_mapping = dict(zip(zip(future_forecast["RM Code"], future_forecast["Plant Code"]), future_forecast["Average_Daily_Sales"]))
            final_output_df["Average Daily Sales (Future)"] = final_output_df.apply(lambda row: rm_daily_mapping.get((row["Material Code"], row["Plant Code"]), 0), axis=1)
            final_output_df["Average Daily Sales (Future)"] = (final_output_df["Average Daily Sales (Future)"].fillna(0) * final_output_df["SOB"])

            # DEBUG: check future ADS too
            # zero_future_ads = final_output_df[
            #     final_output_df["Average Daily Sales (Future)"] == 0
            # ][["Material Code", "Plant Code", "Average Daily Sales (Future)"]]
            # if not zero_future_ads.empty:
            #     debug_log(
            #         " Average Daily Sales (Future) == 0 — check BOM_Forecast_Data_Future:"
            #     )
            #     debug_log(zero_future_ads.to_string())
            # else:
            #     debug_log("` No rows with Average Daily Sales (Future) == 0")

            #-----------------------------------------------------------------#
            #-----------------------Add Planning cycle, rm segmen------------------------#
            #-----------------------------------------------------------------#
            rm_cycle_mapping = dict(zip(zip(future_forecast["RM Code"], future_forecast["Plant Code"]), future_forecast["Cycle"]))
            final_output_df["Planning cycle"] = final_output_df.apply(lambda row: rm_cycle_mapping.get((row["Material Code"], row["Plant Code"]), 0), axis=1)

            #######################################################################
            rm_segm_df = self.dataframes.get('rm_segmentation_output')
            rm_segm_mapping = dict(zip(zip(rm_segm_df["RM Code"], rm_segm_df["Plant Code"]), rm_segm_df["Segmentation"]))
            final_output_df["RM Segmentation"] = final_output_df.apply(lambda row: rm_segm_mapping.get((row["Material Code"], row["Plant Code"]), 0), axis=1)

            #-----------------------------------------------------------------#
            #-------------------------DSI-CALCULATIONS------------------------#
            #-----------------------------------------------------------------#
            # Calculate the Cycle DSI
            if self.cycle_stock_cm == "Max":
                final_output_df['Cycle (DSI)'] = final_output_df[["R1 Information Cycle (DSI)", 
                                                                    "R2 Manufacturing Lot Size (DSI)", 
                                                                    "R3 Shipping Lot Size (DSI)", 
                                                                    "R4 Shipping Interval (DSI)"]].max(axis=1)
            else:
                final_output_df['Cycle (DSI)'] = final_output_df[["R1 Information Cycle (DSI)", 
                                                                    "R2 Manufacturing Lot Size (DSI)", 
                                                                    "R3 Shipping Lot Size (DSI)", 
                                                                    "R4 Shipping Interval (DSI)"]].sum(axis=1)

            
            # Calculate the Transit DSI
            final_output_df['Transit (DSI)'] = final_output_df["R5 Geography (DSI)"]
            if self.transit_cap is not None:
                final_output_df['Transit (DSI)'] = np.where(
                    final_output_df['Transit (DSI)'] > self.transit_cap, 
                    self.transit_cap, 
                    final_output_df['Transit (DSI)']
                )  

            # Calculate the Safety DSI
            final_output_df['Safety (DSI)'] = round(np.sqrt((final_output_df["R6 Shipping Variation (DSI)"])**2 + (final_output_df["R7 Supply Variation (DSI)"])**2 
                                                      + (final_output_df["R8 Demand Variation (DSI)"])**2), 2)
            if self.saftey_cap is not None:
                final_output_df['Safety (DSI)'] = np.where(
                    final_output_df['Safety (DSI)'] > self.saftey_cap, 
                    self.saftey_cap, 
                    final_output_df['Safety (DSI)']
                )
            
            # Calculate the 8 Reasons DSI
            final_output_df["8 Reasons (DSI)"] = final_output_df['Safety (DSI)'] + final_output_df['Transit (DSI)'] + final_output_df['Cycle (DSI)']

            # Calculate the Min DSI
            final_output_df["Min (DSI)"] = final_output_df['Safety (DSI)']

            # Calculate the On-hand DSI
            final_output_df["On-Hand (DSI)"] = final_output_df['Safety (DSI)'] + final_output_df['Cycle (DSI)']

            # Calculate the Max DSI
            final_output_df["Max (DSI)"] = final_output_df['Safety (DSI)'] + (final_output_df['Cycle (DSI)'])*2

            #-----------------------------------------------------------------#
            #--------------------------Under Min & Over Max-------------------#

            final_output_df = self.calculate_undermin_overmax(final_output=final_output_df)

            #-----------------------------------------------------------------#
            #-------------------------UNIT-CALCULATIONS-----------------------# 						
            #-----------------------------------------------------------------#
            
            # Calculate the 8 Reasons (Units)
            final_output_df["8 Reasons (Units)"] = round(final_output_df["8 Reasons (DSI)"] * final_output_df["Average Daily Sales (Future)"], 2)

            # Calculate the Cycle Units
            final_output_df["Cycle (Units)"] = round(final_output_df["Cycle (DSI)"] * final_output_df["Average Daily Sales (Future)"],2)

            # Calculate the Transit Units
            final_output_df["Transit (Units)"] = round(final_output_df["Transit (DSI)"] * final_output_df["Average Daily Sales (Future)"], 2)

            # Calculate the Saftey Units
            final_output_df["Safety (Units)"] = round(final_output_df["Safety (DSI)"] * final_output_df["Average Daily Sales (Future)"], 2)

            # Calculate the on-hand units
            final_output_df["On-Hand (Units)"] = round(final_output_df["On-Hand (DSI)"] * final_output_df["Average Daily Sales (Future)"], 2)

            # Calculate the Min Units
            final_output_df["Min (Units)"] = round(final_output_df["Min (DSI)"] * final_output_df["Average Daily Sales (Future)"], 2)

            # Calculate the Max Units
            final_output_df["Max (Units)"] = round(final_output_df["Max (DSI)"] * final_output_df["Average Daily Sales (Future)"], 2)

            # Add the Historical data quality
            final_output_df = self.calculate_data_quality(final_output_df, ['New SKU', 'Under Min (Val)', 'Over Max (Val)', 'Information Cycle (Days)','R2 Manufacturing Lot Size (DSI)',
                                                                            'Time Stamp (Date/Time)', 'R7 Supply Variation (DSI)', 'Supply Reliability (%)',
                                                                            '8 Reasons (Units)', 'Cycle (Units)', 'Transit (Units)', 'Safety (Units)', 'On-Hand (Units)', 'Min (Units)'
                                                                                ,'Max (Units)'])
            
            ## Adding Time Stamp (Date/Time)
            final_output_df["Time Stamp (Date/Time)"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            ## Add the Safety Stock cap
            final_output_df["Safety Stock Cap"] = self.saftey_cap

            # Add the 'Maximum Demand in % of Forecast'
            final_output_df['Maximum Demand in % of Forecast'] = self.maximum_percent_forecast
            
            final_output_df.drop_duplicates(inplace=True)
            
            # Adding RM Type as Category Column
            final_output_df.drop(columns=['Category'], inplace=True)
            final_output_df.rename(columns={'RM Type' : 'Category'}, inplace=True)
            final_output_df[final_output_df.select_dtypes(include=['object']).columns] = final_output_df.select_dtypes(include=['object']).map(lambda x: x.strip() if isinstance(x, str) else x)

            self.final_response['Consumption_merged'] = convert_df_to_base64(self.dataframes['Consumption_merged'])
            self.final_response['RM_Seg_merged'] = convert_df_to_base64(self.dataframes['RM_Seg_merged'])
            # .............................CODE ..............................
            grouped_dataframes = generate_output_dataframes(final_output_df)  
            #-----------------------------------------------------------------#
            self.final_response["Final_Output"] = generate_encoded_output(grouped_dataframes)

            return self.final_response