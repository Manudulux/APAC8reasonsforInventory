import pandas as pd
from src.component.config import Config
from src.helper import GLOBAL_CONFIG

class CalculationUtility:
    def __init__(self) -> None:
        self.load_config()

    def load_config(self):
        self.local_transit_time = GLOBAL_CONFIG['global_parameters'][0]["default_values"].get("transit_time_local")
        self.imported_transit_time = GLOBAL_CONFIG['global_parameters'][0]["default_values"].get("transit_time_imported")
        self.local_shipping_interval_days = GLOBAL_CONFIG['global_parameters'][0]["default_values"].get("shipping_interval_local")
        self.imported_shipping_interval_days = GLOBAL_CONFIG['global_parameters'][0]["default_values"].get("shipping_interval_imported")

    def old_new_sku_code_map(self, df:pd.DataFrame):
        try:
            df.dropna(inplace=True, axis=0)
            df_map = {}
            for _, columnData in df.iterrows():
                df_map[(columnData["Plant Code"], int(columnData["Phase-Out RM Code"]))]=int(columnData["Phase-In RM Code"])
            return df_map
        except Exception as e:
            return df_map

    def old_new_supplier_code_map(self, df:pd.DataFrame):
        try:
            df.dropna(inplace=True, axis=0)
            df_map = {}
            for _, columnData in df.iterrows():
                df_map[(columnData["Plant Code"], int(columnData["Phase-Out Supplier Code"]))]=int(columnData["Phase-In Supplier Code"])
            return df_map
        except Exception as e:
            return df_map
        
    def delete_old_sku_supply_parameter(self, df_map: pd.DataFrame):
        try:
            sku_map = self.old_new_sku_code_map(df_map["SKU_Transition"])
            for key, _ in sku_map.items():
                plant, material =  key
                df_map['Supply_Parameters'] = df_map['Supply_Parameters'][~((df_map['Supply_Parameters']['Material Code'] == material) & (df_map['Supply_Parameters']['Plant Code'] == plant))]
            return df_map            
        except Exception as e:
            return df_map

    def code_transition(self, df_map:dict) -> dict:
        try:
            sku_map = self.old_new_sku_code_map(df_map["SKU_Transition"])
            supplier_map = self.old_new_supplier_code_map(df_map["Supplier_Transition"])
            
            for file, df in df_map.items():
                if file not in ["SKU_Transition", "Supplier_Transition"]:
                    if file != "Product_Master":
                        for col in df.columns:
                            if col in Config.RM_CODES:
                                for (plant, old_rm), new_rm in sku_map.items():
                                    df.loc[(df[col] == old_rm) & (df['Plant Code'] == plant), col] = new_rm

                            if col in Config.SUPPLIER_CODES:
                                for (plant, old_supp), new_supp in supplier_map.items():
                                    df.loc[(df[col] == old_supp) & (df['Plant Code'] == plant), col] = new_supp
                        df_map[file] = df
                    else:
                        for col in df.columns:
                            if col in Config.RM_CODES:
                                for (plant, old_rm), new_rm in sku_map.items():
                                    if old_rm in df[col].values and new_rm not in df[col].values:
                                        new_row = df[df[col] == old_rm].copy()
                                        new_row[col] = new_rm
                                        df = pd.concat([df, new_row], ignore_index=True)
                        df_map[file] = df
                else:
                    continue
            return df_map
        except Exception as e:
            return e
        
    def rm_name_transition(self, df_map:dict) -> dict:
        try:
            product_master = df_map.get('Product_Master')
            consumption = df_map.get('Consumption_Invoice_Hist')
            
            rm_mapping = dict(zip(product_master['SKU'], product_master['SKU Description']))
            consumption['RM Name'] = consumption['RM Code'].map(rm_mapping)
            df_map['Consumption_Invoice_Hist'] = consumption

            return df_map
        except Exception as e:
            return df_map

    def filter_historical(self,df):
        forcast_history = df["BOM_Forecast_Data_History"]
        forecast_future = df["BOM_Forecast_Data_Future"]
        filtered_history = forcast_history[forcast_history['RM Code'].isin(forecast_future['RM Code'])]
        df["BOM_Forecast_Data_History"] = filtered_history
        return df
    
    def remove_0_sob(self, dataframes):
        try:
            dataframes["Supply_Parameters"].rename(columns={'Material Code': 'RM Code'}, inplace=True)
            merged_data = pd.merge(
                dataframes["Sourcing_Data"],
                dataframes["Supply_Parameters"][['Plant Code', 'RM Code', 'Supplier Code', 'SOB']],
                left_on=['Plant Code', 'RM Code', 'Supplier Code'],
                right_on=['Plant Code', 'RM Code', 'Supplier Code'],
                how='left'
            )
            
            merged_data = merged_data[merged_data['SOB'] != 0.0]
            merged_data = merged_data.drop(columns=['SOB'])
            
            dataframes["Sourcing_Data"] = merged_data
            dataframes["Supply_Parameters"].rename(columns={'RM Code':'Material Code'}, inplace=True)
            dataframes["Supply_Parameters"] = dataframes["Supply_Parameters"][
                ~(dataframes["Supply_Parameters"]['SOB'] == 0.00)
            ]
            return dataframes
        
        except Exception as e:
            return e
    
    def filtered_dataframes(self, dataframes, execute):
        try:
            # Get the unique (RM Code, Plant Code) pairs from the BOM_Forecast_Data_Future DataFrame
            rm_plant_pairs = dataframes["BOM_Forecast_Data_Future"][["RM Code", "Plant Code"]].drop_duplicates()
            
            # Convert the pairs into a set of tuples for fast look-up
            rm_plant_set = set([tuple(row) for row in rm_plant_pairs.values])

            # Filter the Consumption DataFrame (Check both RM Code and Plant Code as a pair)
            dataframes["Consumption_Invoice_Hist"] = dataframes["Consumption_Invoice_Hist"][
                dataframes["Consumption_Invoice_Hist"].apply(
                    lambda row: (row["RM Code"], row["Plant Code"]) in rm_plant_set, axis=1
                )
            ]
            
            # Filter the BOM_Forecast_Data_History DataFrame (Check both RM Code and Plant Code as a pair)
            dataframes["BOM_Forecast_Data_History"] = dataframes["BOM_Forecast_Data_History"][
                dataframes["BOM_Forecast_Data_History"].apply(
                    lambda row: (row["RM Code"], row["Plant Code"]) in rm_plant_set, axis=1
                )
            ]
            
            # Filter the Supply Parameter DataFrame (Check both Material Code and Plant Code as a pair)
            dataframes["Supply_Parameters"] = dataframes["Supply_Parameters"][
                dataframes["Supply_Parameters"].apply(
                    lambda row: (row["Material Code"], row["Plant Code"]) in rm_plant_set, axis=1
                )
            ]

            # Create zero SOB dictionary based on (Material Code, Plant Code) pairs
            # Directly create the list of tuples (RM Code, Plant Code, Supplier Code) for SOB == 0.0
            zero_sob_tuples = list(
                zip(
                    dataframes["Supply_Parameters"][dataframes["Supply_Parameters"]['SOB'] == 0.0]['Material Code'],  # RM Code
                    dataframes["Supply_Parameters"][dataframes["Supply_Parameters"]['SOB'] == 0.0]['Plant Code'].astype(str),     # Plant Code
                    dataframes["Supply_Parameters"][dataframes["Supply_Parameters"]['SOB'] == 0.0]['Supplier Code'].astype(int)  # Supplier Code
                )
            )

            # Remove rows where SOB is zero
            dataframes["Supply_Parameters"] = dataframes["Supply_Parameters"][~(dataframes["Supply_Parameters"]['SOB'] == 0.00)]
            dataframes["Supply_Parameters"].drop_duplicates(inplace=True)

            existing_tuples = set(
                        zip(
                            dataframes["Supply_Parameters"]['Material Code'],
                            dataframes["Supply_Parameters"]['Plant Code'].astype(str),
                            dataframes["Supply_Parameters"]['Supplier Code'].astype(int)
                        )
                    )
            
            zero_sob_tuples = [tup for tup in zero_sob_tuples if tup not in existing_tuples]
            
            # Filter the Sourcing Data DataFrame (Check both RM Code and Plant Code as a pair)
            dataframes["Sourcing_Data"] = dataframes["Sourcing_Data"][
                dataframes["Sourcing_Data"].apply(
                    lambda row: (row["RM Code"], row["Plant Code"]) in rm_plant_set, axis=1
                )
            ]
            
            # Corrected filtering for Sourcing Data based on zero_sob_dict
            if execute:
                if len(zero_sob_tuples) > 0:
                    dataframes["Sourcing_Data"] = dataframes["Sourcing_Data"][ ~dataframes["Sourcing_Data"].apply(
                                                    lambda row: ((row['RM Code'], row['Plant Code'], row['Supplier Code']) 
                                                        in [(item[0], item[1], item[2]) for item in zero_sob_tuples]
                                                    ), axis=1
                                                )]
            
            # Filter the Shipping_Interval data DataFrame (Check both RM Code and Plant Code as a pair)
            dataframes["Shipping_Interval"] = dataframes["Shipping_Interval"][
                dataframes["Shipping_Interval"].apply(
                    lambda row: (row["RM Code"], row["Plant Code"]) in rm_plant_set, axis=1
                )
            ]
            
            # Filter the Supply and Shipping Var data DataFrame (Check both Material Code and Plant Code as a pair)
            dataframes["Supply&Shipping_Var"] = dataframes["Supply&Shipping_Var"][
                dataframes["Supply&Shipping_Var"].apply(
                    lambda row: (row["Material Code"], row["Plant Code"]) in rm_plant_set, axis=1
                )
            ]
            
            # Filter the Actual_Inventory DataFrame (Check both CODE and Plant Code as a pair)
            dataframes["Actual_Inventory"] = dataframes["Actual_Inventory"][
                dataframes["Actual_Inventory"].apply(
                    lambda row: (row["CODE"], row["Plant Code"]) in rm_plant_set, axis=1
                )
            ]

            return dataframes
        except Exception as e:
            print(f"An error occurred: {e}")
            return str(e)

    def add_default_data(self,dataframes):
        try:
            Supply_Parameters = dataframes["Supply_Parameters"]
            Sourcing_Data = dataframes["Sourcing_Data"]

            # Loop through rows in Sourcing_Data to fill missing values based on conditions
            for index, row in Sourcing_Data.iterrows():
                rm = row['RM Code']
                supplier = row['Supplier Code']
                plant = row['Plant Code']

                # Find the RM Type in Supply_Parameters for the matching 'Material Code' and 'Supplier Code'
                matching_row = Supply_Parameters.loc[
                    (Supply_Parameters['Plant Code'] == plant) & (Supply_Parameters['Material Code'] == int(rm)) & (Supply_Parameters['Supplier Code'] == int(supplier))
                ]
                if not matching_row.empty:
                    rm_type = matching_row['RM Type'].iloc[0].lower()

                    # Update 'Shipping Interval (Days)' if it's missing
                    if pd.isnull(row['Shipping Interval (Days)']):
                        if rm_type.startswith('local'):
                            Sourcing_Data.loc[index, 'Shipping Interval (Days)'] = self.local_shipping_interval_days
                        else:
                            Sourcing_Data.loc[index, 'Shipping Interval (Days)'] = self.imported_shipping_interval_days

                    # Update 'Transit Time (Days)' if it's missing
                    if pd.isnull(row['Transit Time (Days)']):
                        if rm_type.startswith('local'):
                            Sourcing_Data.loc[index, 'Transit Time (Days)'] = self.local_transit_time
                            Sourcing_Data.loc[index, 'Transit Time Std. Dev. (%)'] = 1
                        else:
                            Sourcing_Data.loc[index, 'Transit Time (Days)'] = self.imported_transit_time
                            Sourcing_Data.loc[index, 'Transit Time Std. Dev. (%)'] = 1
            Sourcing_Data.dropna(subset= ['Transit Time (Days)', 'Shipping Interval (Days)'], inplace=True)
            Sourcing_Data.reset_index(drop=True, inplace=True)
            dataframes["Sourcing_Data"] = Sourcing_Data
            return dataframes
        except Exception as e:
            print(e)
            return dataframes

