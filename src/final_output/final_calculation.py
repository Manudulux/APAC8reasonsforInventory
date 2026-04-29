import pandas as pd
from scipy.stats import norm

class FinalCalculation:
    def __init__(self, dataframes):
        self.df = dataframes
        self.new_sku_list = dataframes['SKU_Transition']['Phase-In RM Code'].unique().tolist()
        self.Supply_Parameters = dataframes["Supply_Parameters"]
        self.Sourcing_Data = dataframes["Sourcing_Data"]
        self.Act_Inventory = dataframes["Actual_Inventory"]
        self.supply_sourcing_merged_df = pd.merge(self.Supply_Parameters, self.Sourcing_Data, left_on=['Plant Code','Material Code', 'Supplier Code'], right_on=['Plant Code', 'RM Code', 'Supplier Code'], how='inner')

    def initiate(self):
        #--------------------------------------------------------------------------------------#
        #------------------------------------Calculate-Final-----------------------------------#
        #--------------------------------------------------------------------------------------#
        # CALCULATE THE SERVICE_LEVEL_FACTOR.
        self.Supply_Parameters['Service Level (%)'] = self.Supply_Parameters['Service Level (%)'].fillna(0)
        service_level_factor_df = self.Supply_Parameters.groupby(['Plant Code','Material Code', 'Supplier Code']).apply(
            lambda x: norm.ppf(x['Service Level (%)'].astype(float).iloc[0] / 100)  # Removed axis, fixed percentage
        ).reset_index(name='Service Level Factor (z)')

        service_level_factor_df['Service Level Factor (z)'] = service_level_factor_df['Service Level Factor (z)'].round(2)

        # Merge with service_level_factor_df to include Service Level Factor (z) in df.
        final_df = pd.merge(self.supply_sourcing_merged_df, service_level_factor_df, on=["Plant Code", 'Material Code', 'Supplier Code'], how='left')
        # CALCULATE REVIEW_TIME.
        # Convert 'Information Cycle (Days)' and 'Shipping Interval (Days)' to integers
        final_df[['Information Cycle (Days)', 'Shipping Interval (Days)', 'Transit Time (Days)', 'Additional Time (Days)']] = final_df[['Information Cycle (Days)', 'Shipping Interval (Days)', 'Transit Time (Days)', 'Additional Time (Days)']].fillna(0).astype(float)
        final_df['Review Period (days)'] = final_df[['Information Cycle (Days)', 'Shipping Interval (Days)']].max(axis=1).round(2)
        # CALCULATE THE LEAD TIME (DAYS).
        final_df['Lead Time (days)'] = final_df.apply(
            lambda row: row['Transit Time (Days)'] + row['Additional Time (Days)']
                        if row['INCO Term'].strip().lower().startswith('c') or row['INCO Term'].strip().lower() == 'exw'
                        else row['Additional Time (Days)'],
            axis=1
        ).round(2)

        # CALCULATE THE RISK HORIZON (DAYS).
        final_df['Risk-Horizon (days)'] = final_df['Review Period (days)'] + final_df['Lead Time (days)']

        # Calculate the NEW SKU
        final_df['New SKU'] = final_df['Material Code'].apply(lambda x: 'Yes' if x in self.new_sku_list else '')
        # Create the final calculate dataframe.
        final_cal_df = final_df[['PLANT', 'Plant Code', 'RM Code', 'Supplier Code','SOB', 'Service Level Factor (z)','Review Period (days)','Lead Time (days)','Risk-Horizon (days)', 'New SKU']]
        #---------------------------------------------------------------------------------------------#
        #------------------------------------Create-Final-DF------------------------------------------#
        #---------------------------------------------------------------------------------------------#
        self.supply_sourcing_merged_df.drop(columns=['Country', 'Supplier name', 'RM Code',
            'RM Name', 'Country of Origin'], inplace=True)

        # Convert 'Supplier Code' in both DataFrames to int
        self.supply_sourcing_merged_df['Supplier Code'] = self.supply_sourcing_merged_df['Supplier Code'].astype(int)
        final_cal_df['Supplier Code'] = final_cal_df['Supplier Code'].astype(int)
        self.supply_sourcing_merged_df['Material Code'] = self.supply_sourcing_merged_df['Material Code'].astype(int)
        final_cal_df['RM Code'] = final_cal_df['RM Code'].astype(int)
        final_cal_df = pd.merge(final_cal_df, self.Act_Inventory[['CODE', 'Plant Code', 'MAP']],
                                left_on=['RM Code', 'Plant Code'],
                                right_on=['CODE', 'Plant Code'], 
                                how='left')

        # Select specific columns from final_cal_df and merge
        columns_to_add = ['Service Level Factor (z)', 'Review Period (days)', 'Lead Time (days)', 'Risk-Horizon (days)', 'New SKU', 'MAP']
        final_output_df = pd.merge(
            self.supply_sourcing_merged_df,
            final_cal_df[["Plant Code", 'RM Code', 'Supplier Code'] + columns_to_add],
            left_on=["Plant Code", 'Material Code', 'Supplier Code'],
            right_on=["Plant Code", 'RM Code', 'Supplier Code'],
            how='left'
        )
        return final_output_df