import pandas as pd

def generate_rm_input_file(dataframes):
    consumption = dataframes.get("Consumption_Invoice_Hist")
    future_forecast = dataframes.get("BOM_Forecast_Data_Future")

    consumption["Post Date"] = consumption["Post Date"].astype(str)
    consumption["Post_Month"] = consumption["Post Date"].apply(lambda x:".".join(x.split(".")[1:]))

    consumption["Movement Qty"] = consumption["Movement Qty"].apply(lambda x : x*(-1))

    df = consumption.groupby(["Plant Code", "RM Code", "Post_Month"])["Movement Qty"].sum().unstack().reset_index()
    df = df.reindex(sorted(df.columns, reverse=True), axis=1)

    # Identify columns with "mm.yyyy"
    date_columns = [col for col in df.columns if col.count('.') == 1 and len(col) == 7]
    # Convert to datetime for sorting
    sorted_columns = sorted(date_columns, key=lambda x: pd.to_datetime(x, format='%m.%Y'))
    # Reorder DataFrame with sorted date columns
    sorted_df = df[['RM Code', 'Plant Code'] + sorted_columns]
    consumption_unique = consumption[['Plant Name', 'Plant Code', 'RM Code', 'RM Name']].drop_duplicates()
    merged_df = sorted_df.merge(
        consumption_unique[['Plant Name', 'Plant Code', 'RM Code', 'RM Name']],
        on=['Plant Code', 'RM Code'],  # Merge on 'RM Code'
        how='left'     # Use 'left' to keep all rows from sorted_df
    )
    merged_df = merged_df[['RM Code', 'Plant Code'] + sorted_columns + ['Plant Name', 'RM Name']]
    # Rename 'Plant Code_x' to 'Plant Code' for clarity
    mm_yyyy_columns = [col for col in merged_df.columns if col.count('.') == 1 and len(col) == 7]
    years = set(col.split('.')[1] for col in mm_yyyy_columns)
    future_forecast.columns = future_forecast.columns.astype('str')
    future_forecast_columns = [col for col in future_forecast.columns if col.isdigit() and len(col) == 6]

    # Iterate over each RM code in the consumption DataFrame
    for rm_code in merged_df['RM Code'].unique():
        # Get forecast data for this RM code
        rm_data = merged_df[merged_df['RM Code'] == rm_code]

        # Count valid (non-null and non-zero) entries in MM.YYYY columns
        valid_count = rm_data[mm_yyyy_columns].notnull().sum(axis=1).values[0]
        # If there are 4 or fewer valid entries, proceed
        if valid_count <= 4:
            forecast_data = future_forecast[future_forecast['RM Code'] == rm_code]

            # Proceed only if there are valid forecasts
            if not forecast_data.empty:
                # Identify the indices of the forecast values
                forecast_values = forecast_data[future_forecast_columns].values.flatten()
                
                # Initialize an index for the forecast values
                forecast_index = 0

                # Iterate over each MM.YYYY column
                for col in mm_yyyy_columns:
                    fill_mask = (merged_df['RM Code'] == rm_code) & (merged_df[col].isnull())

                    if fill_mask.any():  # Check if there are any null values
                        # Determine how many values we need to fill
                        num_to_fill = fill_mask.sum()

                        # Fill in the missing values with forecast values, ensuring unique filling
                        for i in range(num_to_fill):
                            if forecast_index < len(forecast_values):  # Ensure we don't exceed available forecast values
                                merged_df.loc[fill_mask, col] = forecast_values[forecast_index]
                                forecast_index += 1
    dataframes.update({"rm_input_file": merged_df})
    return dataframes