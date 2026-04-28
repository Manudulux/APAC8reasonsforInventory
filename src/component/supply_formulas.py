import pandas as pd
from src.component.rm_segmentation import RmSegmentation
from src.helper import GLOBAL_CONFIG
import numpy as np

class SupplyParameter:
    def __init__(self,df) -> None:
        self.df =df
        self.Supply_Parameters = df["Supply_Parameters"]
        self.Shipping_Interval = df["Shipping_Interval"]
        self.Supply_Shipping_Var = df["Supply&Shipping_Var"]
        self.load_config()

    def load_config(self):
        self.tolerance = GLOBAL_CONFIG['global_parameters'][0].get('tolerance')
        self.default_supply_reliability = GLOBAL_CONFIG['global_parameters'][0]['default_values'].get('supply_reliability')

    def minimum_order(self):
        """
        Calculate MINIMUM ORDER QTY (Units): In Supply_Parameters with the minimum 'Movement Qty'
        from Shipping_Interval, based on matching 'RM Code', 'Supplier', and 'Plant Code'.

        Returns:
            pd.DataFrame: The updated Supply_Parameters dataframe.
        """
        try:
            # Step 1: Merge the DataFrames on 'RM Code', 'Supplier', and 'Plant Code'
            merged_df = pd.merge(
                self.Shipping_Interval, self.Supply_Parameters,
                left_on=['RM Code', 'Supplier', 'Plant Code'],
                right_on=['Material Code', 'Supplier Code', 'Plant Code'],
                how='inner'
            )

            # Step 2: Perform the groupby and aggregation (Movement Qty min)
            aggregated_df = merged_df.groupby(['RM Code', 'Supplier', 'Plant Code']).agg({
                'Movement Qty': lambda x: np.min(x[x > 0]) if (x > 0).any() else np.nan
            }).reset_index()

            # Step 3: Merge the aggregated data back into Supply_Parameters
            updated_supply_params = pd.merge(
                self.Supply_Parameters,
                aggregated_df,
                left_on=['Material Code', 'Supplier Code', 'Plant Code'], 
                right_on=['RM Code', 'Supplier', 'Plant Code'],
                how='left'
            )

            # Step 4: Overwrite 'MINIMUM ORDER QTY (Units)' in Supply_Parameters with 'Movement Qty'
            updated_supply_params['MINIMUM ORDER QTY (Units)'] = updated_supply_params['Movement Qty']

            # Delete the Shipping_Interval columns from Supply_Parameters df
            updated_supply_params.drop(columns=['Movement Qty', 'RM Code', 'Supplier'], inplace=True)
            updated_supply_params['MINIMUM ORDER QTY (Units)'].fillna(0, inplace=True)
            # Update the class attribute
            self.df["Supply_Parameters"] = updated_supply_params
            return self.df

        except Exception as e:
            print(f"error in mqt column: {str(e)}")
            return self.df


    def supply_reliability(self):
        """
        Calculates and updates supply reliability percentage.
        1. Retrieves data from `minimum_order`.
        2. Calculates 'Supply Variation' (difference between 'ATD (POL)' and 'Supplier ETD (POL)').
        3. Merges supply parameters with shipping data.
        4. Applies `calculate_variation_tolerance` to compute reliability percentages.
        5. Updates 'Supply Reliability (%)' in the original dataframe.

        Returns:
            pd.DataFrame: Updated dataframe with supply reliability.
        """
        dataframes = self.minimum_order()
        try:
            Supply_Parameters = dataframes["Supply_Parameters"]
            Supply_Shipping_Var = dataframes["Supply&Shipping_Var"]

            # Convert the relevant columns to datetime format if they are not already
            Supply_Shipping_Var['ATD (POL)'] = pd.to_datetime(Supply_Shipping_Var['ATD (POL)'])
            Supply_Shipping_Var['Supplier ETD (POL)'] = pd.to_datetime(Supply_Shipping_Var['Supplier ETD (POL)'])

            # Calculate the 'Supply Variation' as the difference in days
            Supply_Shipping_Var['Supply Variation'] = (Supply_Shipping_Var['ATD (POL)'] - Supply_Shipping_Var['Supplier ETD (POL)']).dt.days

            # Merge with Plant Code included
            merged_df = pd.merge(
                Supply_Parameters,
                Supply_Shipping_Var,
                left_on=['Material Code', 'Supplier Code', 'Plant Code'],
                right_on=['Material Code', 'Supplier', 'Plant Code'],
                how='inner'
            )

            # Apply the variation tolerance calculation
            result_df = merged_df.groupby(['Plant Code', 'Material Code', 'Supplier']).apply(self.calculate_variation_tolerance).reset_index()
            result_df = result_df.rename(columns={0: 'Supply Reliability Percentage'})

            # Merge the results back with Supply Parameters
            merged_df = Supply_Parameters.merge(
                result_df,
                how='left',
                left_on=['Material Code', 'Supplier Code', 'Plant Code'],
                right_on=['Material Code', 'Supplier', 'Plant Code']
            )

            # Replace 'Supply Reliability (%)' in Supply_Parameters with values from 'Supply Reliability Percentage'
            merged_df['Supply Reliability (%)'] = merged_df['Supply Reliability Percentage']
            
            # Drop extra columns if not needed
            merged_df.drop(columns=['Supplier', 'Supply Reliability Percentage'], inplace=True)
            
            # Add empty columns
            merged_df['Information Cycle (Days)'] = ""
            merged_df['Service Level (%)'] = ""
            dataframes["Supply_Parameters"] = merged_df
            return dataframes
        except Exception as e:
            print(f"error in supply_reliability column: {str(e)}")
            return dataframes


    # Define the function to calculate Supply Variation % using tolerance based on RM Type
    def calculate_variation_tolerance(self,group):
        try:
            # Get the RM Type for the group
            rm_type = group['RM Type'].iloc[0].lower()
            # Get the tolerance based on RM Type
            tolerance = self.tolerance['local'] if rm_type.startswith("local") else self.tolerance['imported']
            # Calculate if Supply Variation exceeds tolerance
            tolerance_column = (group['Supply Variation'] > tolerance).astype(int)
            #Apply the formula to calculate the Supply_Variation_Percentage.
            Supply_Variation_Percentage = round((list(tolerance_column).count(0)/len(tolerance_column))*100,5)
            
            return Supply_Variation_Percentage
        except Exception as e:
            print(f"Error in group: {e}")

    def service_level_percentage(self):
        dataframes = self.supply_reliability()
        output_dfs = RmSegmentation(dataframes=dataframes).calculate()
        rm_segmentation_output = output_dfs.get('rm_segmentation_output')
        Supply_Parameters = dataframes.get("Supply_Parameters")
        service_mapping = dict(zip(rm_segmentation_output['RM_Plant'], rm_segmentation_output['Service_Level(%)']))
        Supply_Parameters['Material_Plant'] = Supply_Parameters["Material Code"].astype('int').astype('str') + "_" + Supply_Parameters['Plant Code'].astype('str')
        Supply_Parameters['Service Level (%)'] = Supply_Parameters["Material_Plant"].map(service_mapping)
        Supply_Parameters.drop(columns='Material_Plant', inplace=True)
        rm_segmentation_output.drop(columns='RM_Plant', inplace=True)
        Supply_Parameters.fillna({'Supply Reliability (%)': self.default_supply_reliability}, inplace=True)
        rm_segmentation_output.reset_index(drop=True, inplace=True)
        dataframes["RM_Segmentation_Output"] = rm_segmentation_output
        dataframes["Supply_Parameters"] = Supply_Parameters
        return dataframes

    def Calculate(self):
          dataframes = self.service_level_percentage()
          return dataframes