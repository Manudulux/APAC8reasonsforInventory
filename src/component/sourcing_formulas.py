import pandas as pd
from src.component.sourcing_utils import SourcingUtils
import numpy as np

class SourcingCalculations:
    def __init__(self) -> None:
        self.utils_class = SourcingUtils()

    def transit_time(self, dataframes):
        try:
            dataframes = self.utils_class.modified_dfs(dataframes)
            supply_shipping_df = dataframes["Supply&Shipping_Var"]
            sourcing_df = dataframes["Sourcing_Data"]
            sourcing_df.drop_duplicates(subset=['Country', 'Plant Code', 'Supplier Code', 'RM Code','Country of Origin'], inplace=True)
            supplier_grouped = supply_shipping_df.groupby('Combined_Key')['TT'].apply(list)\
                .reset_index()
            modified_transit_df = pd.merge(
                sourcing_df, supplier_grouped, on='Combined_Key', how='left')
            modified_transit_df['TT_mean'] = modified_transit_df['TT'].apply(
                lambda x: pd.Series(x).mean()
                    if isinstance(x, list) else None)
            modified_transit_df['TT_std'] = modified_transit_df['TT'].apply(
                lambda x: pd.Series(x).std()
                    if isinstance(x, list) else None)
            modified_transit_df["Transit Time (Days)"] = (modified_transit_df["TT_mean"]\
                + modified_transit_df["TT_std"]).round(2)
            dataframes["Sourcing_Data"] = modified_transit_df
            return dataframes
        except Exception as e:
            raise e

    def adding_local_tt_mean_std(self, sourcing_df, local_tt_df):
        try:
            # Convert 'RM Code' and 'Supplier Code' in sourcing_df and 'CODE', 'Supplier' in local_tt_df to string type
            sourcing_df['RM Code'] = sourcing_df['RM Code'].apply(lambda x: str(int(x))
                if pd.notna(x) and float(x).is_integer() else str(x))
            sourcing_df['Supplier Code'] = sourcing_df['Supplier Code'].apply(lambda x: str(int(x))
                if pd.notna(x) and float(x).is_integer() else str(x))
            local_tt_df['CODE'] = local_tt_df['CODE'].apply(lambda x: str(int(x))
                if pd.notna(x) and float(x).is_integer() else str(x))
            local_tt_df['Supplier'] = local_tt_df['Supplier'].apply(lambda x: str(int(x))
                if pd.notna(x) and float(x).is_integer() else str(x))

            sourcing_df['Plant Code'] = sourcing_df['Plant Code'].astype(str).str.strip()
            local_tt_df['Plant Code'] = local_tt_df['Plant Code'].astype(str).str.strip()
            merged_df = pd.merge(sourcing_df, local_tt_df,
                left_on=['Plant Code', 'RM Code', 'Supplier Code'], right_on=['Plant Code', 'CODE', 'Supplier'], how='left', suffixes=('', '_local_tt'))
            # Only update rows where 'Transit Time' is not NaN
            sourcing_df.loc[merged_df['Transit Time'].notna(), 'Transit Time (Days)'] = merged_df['Transit Time']
            # Only update rows where 'Transit Time Std. Dev. (%)_local_tt' is not NaN
            sourcing_df.loc[merged_df['Transit Time Std. Dev. (%)_local_tt'].notna(), 'Transit Time Std. Dev. (%)'] = merged_df['Transit Time Std. Dev. (%)_local_tt']*100
            # Update the dataframes dictionary with the modified sourcing_df
            return sourcing_df
        except Exception as e:
            raise ValueError(f"Error occurred in adding_local_tt_mean_std: {str(e)}")

    def transit_time_std(self, dataframes):
        try:
            drop_col_list = ["TT", "TT_mean", "TT_std"]
            sourcing_df = dataframes["Sourcing_Data"]
            local_tt_df = dataframes["Local_TT"]
            sourcing_df["Transit Time Std. Dev. (%)"] = (sourcing_df['TT_std']/sourcing_df['TT_mean'])*100
            sourcing_df.drop(drop_col_list, axis=1, inplace=True)
            sourcing_df = self.adding_local_tt_mean_std(sourcing_df, local_tt_df)
            dataframes["Sourcing_Data"] = sourcing_df
            return dataframes
        except Exception as e:
            raise e


    def shipping_interval(self, dataframes):
        try:
            # Fetching Shipping Interval and Sourcing DF
            shipping_interval_df = dataframes["Shipping_Interval"]
            sourcing_df = dataframes["Sourcing_Data"]
            # Extracting Post Week Column
            shipping_interval_df['RM Code'] = shipping_interval_df['RM Code'].astype(int)
            shipping_interval_df['Supplier'] = shipping_interval_df['Supplier'].astype(int)
            sourcing_df['RM Code'] = sourcing_df['RM Code'].astype(int)
            sourcing_df['Supplier Code'] = sourcing_df['Supplier Code'].astype(int)
            supplier_grouped = shipping_interval_df.groupby(['Plant Code','RM Code', 'Supplier'])['Post Week'].apply(list)\
                .reset_index()
            
            modified_sourcing_df = pd.merge(
                sourcing_df, supplier_grouped, left_on=['Plant Code', 'RM Code', 'Supplier Code'], right_on=['Plant Code', 'RM Code', 'Supplier'], 
                how='left')
            post_week_diff = self.utils_class.calculate_post_week_diff(shipping_interval_df['Post Week'].tolist())
            modified_sourcing_df['Shipping Interval (Days)'] = modified_sourcing_df['Post Week'].apply(lambda x: round((7 * post_week_diff)/(self.utils_class.calculating_post_week_sum(x)), 4) if isinstance(x, list) else np.nan)
            dataframes["Sourcing_Data"] = modified_sourcing_df.drop(columns=['Supplier'], axis=1)
            return dataframes
        except Exception as e:
            raise e

    def shipping_interval_std(self, dataframes):
        try:
            sourcing_df = dataframes["Sourcing_Data"]
            sourcing_df['Shipping Interval Std. Dev. (%)'] = sourcing_df['Post Week'].apply(
                lambda x: round((self.utils_class.calculating_post_week_std(x)), 4))
            dataframes["Sourcing_Data"] = sourcing_df
            return dataframes
        except Exception as e:
            raise e

    def shipping_lot_size(self, dataframes):
        try:
            sourcing_df = dataframes["Sourcing_Data"]
            shipping_interval_df = dataframes["Shipping_Interval"]
            merged_df = pd.merge(
                            sourcing_df, shipping_interval_df, left_on=['Plant Code', 'RM Code', 'Supplier Code'],
                            right_on=['Plant Code', 'RM Code', 'Supplier'], how='inner'
                        )
            merged_df = merged_df[merged_df['Movement Qty'] >= 0]
            aggregated_df = merged_df.groupby(['Plant Code', 'RM Code', 'Supplier Code']).apply(self.utils_class.get_lot_size).reset_index()
            aggregated_df = aggregated_df.rename(columns={0: 'Shipping Lot Size'})
            merged_df = sourcing_df.merge(aggregated_df,
                                                how='left',
                                                left_on=['Plant Code','RM Code', 'Supplier Code'],
                                                right_on=['Plant Code','RM Code', 'Supplier Code']
                                                )
            merged_df['Shipping Lot Size (Units)'] = merged_df['Shipping Lot Size']
            merged_df.drop(columns=['Shipping Lot Size'], inplace=True)
            merged_df['Shipping Lot Size (Units)'].fillna(0, inplace=True)
            dataframes["Sourcing_Data"] = merged_df
            return dataframes
        except Exception as e:
            raise e
        
    def rm_name_transition(self, dataframes:dict) -> dict:
        try:
            product_master = dataframes['Product_Master']
            sourcing_df = dataframes["Sourcing_Data"]
            
            rm_mapping = dict(zip(product_master['SKU'], product_master['SKU Description']))
            sourcing_df['RM Name'] = sourcing_df['RM Code'].map(rm_mapping)
            dataframes['Sourcing_Data'] = sourcing_df

            return dataframes
        except Exception as e:
            return dataframes
        
    def final_sourcing_df(self, dataframes):
        # Step 1: Transit time
        transit_df = self.transit_time(dataframes)
        # Step 2: Transit Time Std
        transit_std_df = self.transit_time_std(transit_df)
        # Step 3: Shipping Interval in Days (Mean)
        shipping_df = self.shipping_interval(transit_std_df)
        # Step 4: Shipping Interval Standard Deviation (%)
        shipping_std_df = self.shipping_interval_std(shipping_df)
        # Step 5: Shipping Lot Size
        shipping_lot_size = self.shipping_lot_size(shipping_std_df)
        # Step 6: RM Name Transition
        transited_dfs = self.rm_name_transition(shipping_lot_size)
        # Step 6: Remove Unnecessary Columns
        sourcing_df = self.utils_class.remove_unnecessary_cols(transited_dfs)
        dataframes["Sourcing_Data"] = sourcing_df
        return dataframes