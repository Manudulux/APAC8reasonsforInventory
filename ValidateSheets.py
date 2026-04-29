import pandas as pd
import re
from datetime import datetime
import pandas.api.types as ptypes
from dateutil.relativedelta import relativedelta
from src.helper import VALIDATION_CONFIG, INTERMEDIATE_CONFIG

class validator_functions:
    def __init__(self) -> None:
        pass

    def find_rules(self,sheet_name: str) -> list:
        for sheet in VALIDATION_CONFIG:
            if sheet_name in sheet.Variable:
                return sheet.Columns
        return f"No validation rules found for sheet: {sheet_name}"
    
    def find_intermediate_rules(self, sheet_name: str) -> list:
        for sheet in INTERMEDIATE_CONFIG:
            if sheet_name in sheet.Variable:
                return sheet.Columns
        return f"No validation rules found for sheet: {sheet_name}"

    def validate_sequence(self,df: pd.DataFrame, rules: list) -> list:
        """Extract, sort, and validate forecast columns matching YYYYMM format and check if months are sequential."""
        # Pattern to match columns in YYYYMM format
        forecast_columns_pattern = ""
        for col in rules:
            if col.RepeatNumber>1 and col.NameExpression != "":
                forecast_columns_pattern = col.NameExpression
            columns = list(df.columns)

        # Extract columns that match the pattern
        forecast_columns = [col for col in columns if re.match(forecast_columns_pattern, str(col))]
        # Sort the columns based on date (YYYYMM format)
        sorted_columns = sorted(forecast_columns, key=lambda x: datetime.strptime(str(x), '%Y%m'))
        # Validate if months are sequential
        for i in range(1, len(sorted_columns)):
            prev_month = int(str(sorted_columns[i-1])[-2:])
            curr_month = int(str(sorted_columns[i])[-2:])

            # If the current month is not exactly one month after the previous, return a validation error
            if curr_month != (prev_month % 12) + 1:
                return[f"Months are not in sequence, Missing {sorted_columns[i-1]+1} column between {sorted_columns[i-1]} and {sorted_columns[i]}"]

        return []

    def validate_missing_columns(self, df: pd.DataFrame, rules: list) -> list:
        """Check if any columns defined in the validation rules are missing in the DataFrame."""
        try:
            errors = []
            missing_columns = []
            for column_info in rules:
                col_name = column_info.Name
                alt_names = column_info.AlternateNames
                required = column_info.Required

                if required:
                    # If no column name and no alternate names are provided, skip the rule
                    if not col_name and not alt_names:
                        continue

                    # Collect all possible names (main and alternate)
                    all_names = [col_name] + alt_names if col_name else alt_names
                    # Check if none of the possible names are in the dataframe
                    if not any(col in df.columns for col in all_names):
                        missing_columns.append(col_name or alt_names[0])
            if missing_columns:
                errors.append(f"Missing required fields: {', '.join(missing_columns)}")
            return errors
        except Exception as e:
            return [f"Error in function: validate_missing_columns: {e}"]

    def validate_null_values(self, df: pd.DataFrame, rules: list) -> list:
        """Check if any required columns contain null values."""
        errors = []
        col_names = []

        for column_info in rules:
            col_name = column_info.Name
            alt_names = column_info.AlternateNames
            required = column_info.Required

            if required:
                # Get actual column names based on the main name or alternate names
                actual_columns = [col for col in df.columns if col == col_name or col in alt_names]

                for col in actual_columns:
                    if df[col].isnull().any():
                        col_names.append(col)

        if col_names:
            # Format the error as a single line with the required columns
            errors.append(f"Empty values not allowed for column/s - {', '.join(col_names)}")

        return errors

    def check_data_type(self, value, expected_type) -> bool:
        """Check if the value matches the expected data type."""
        if pd.isnull(value):
            return True  # Allow null values
        try:
            if expected_type == "int":
                return ptypes.is_integer(value) or isinstance(int(value), int)
            elif expected_type == "float":
                return ptypes.is_float(value) or isinstance(float(value), float)
            elif expected_type == "str":
                return ptypes.is_string_dtype(value) or isinstance(str(value), str)
            elif expected_type == "DateTime":
                pd.to_datetime(value, format='%d.%m.%Y', errors='raise')
                return True
            elif expected_type == "DateTimeFlex":
                pd.to_datetime(value, format='%d.%m.%Y', errors='coerce') or pd.to_datetime(value, format='%d-%m-%Y', errors='coerce')
                return pd.notnull(value)
        except (ValueError, TypeError):
            return False
        return False

    def validate_data_types(self, df: pd.DataFrame, rules: list) -> list:
        """Check if the data types of columns match the expected data types."""
        errors = {}

        for column_info in rules:
            if column_info.Required != False:
                col_name = column_info.Name
                alt_names = column_info.AlternateNames
                data_type = column_info.DataType

                # Get actual column names based on the main name or alternate names
                actual_columns = [col for col in df.columns if col == col_name or col in alt_names]

                for col in actual_columns:
                    invalid_rows = [
                        index + 1
                        for index, value in df[col].items()
                        if not self.check_data_type(value, data_type)
                    ]
                    if invalid_rows:
                        if col not in errors:
                            errors[col] = []  # Initialize a list for this column
                        errors[col].append(data_type)  # Append the data type error

        dtype_dict = {"str":"Alphabetical", "DateTime": "Date in DD/MM/YYYY format", "float":"Decimal", "int":"Numeric"}

        errors_str = []  # Initialize the list for error messages
        if errors:
            for col, types in errors.items():
                # We can use set to ensure unique data types for a column
                unique_types = set(types)
                error_message = f"Values must be in {', '.join(dtype_dict[t] for t in unique_types)} for column '{col}'"
                errors_str.append(error_message)
        return errors_str  # Return the list of error messages



    def extract_forecast_columns(self, df: pd.DataFrame) -> list:
        """Extract and sort forecast columns matching MM.YYYY format."""
        forecast_columns_pattern = '^(20\\d{2})(0[1-9]|1[0-2])$'
        return sorted([col for col in df.columns if self.check_regex(str(col), forecast_columns_pattern)])

    def find_missing_year_columns(self, forecast_columns: list) -> list:
        """Identify missing forecast columns if they are not in consecutive sequence."""
        missing_columns = []
        for i in range(1, len(forecast_columns)):
            current_date = datetime.strptime(forecast_columns[i], '%m.%Y')
            prev_date = datetime.strptime(forecast_columns[i - 1], '%m.%Y')
            expected_next_date = prev_date + relativedelta(months=1)

            while current_date != expected_next_date:
                missing_columns.append(expected_next_date.strftime('%m.%Y'))
                expected_next_date += relativedelta(months=1)

        return missing_columns

    def suggest_year_columns(self, last_column: str, missing_count: int) -> list:
        """Suggest future forecast columns based on the last available column."""
        suggested_columns = []
        last_date = datetime.strptime(last_column, '%m.%Y')
        for _ in range(missing_count):
            last_date += relativedelta(months=1)
            suggested_columns.append(last_date.strftime('%m.%Y'))
        return suggested_columns

    def validate_forecast_columns(self, df: pd.DataFrame, rules: list) -> list:
        """Main function to validate forecast columns, check sequence, and suggest missing columns."""
        errors = []
        forecast_columns = self.extract_forecast_columns(df)
        future_forecast_rule = next((rule for rule in rules if rule.NameExpression == r"^(20\\d{2})(0[1-9]|1[0-2])$"), None)
        if future_forecast_rule:
            expected_count = future_forecast_rule.get("RepeatNumber")

            if len(forecast_columns) != expected_count:
                errors.append(f"Expected {expected_count} forecast columns, found {len(forecast_columns)}.")

            missing_columns = self.find_missing_year_columns(forecast_columns)
            if missing_columns:
                errors.append(f"Missing forecast columns: {', '.join(missing_columns)}")

            if len(forecast_columns) + len(missing_columns) < expected_count:
                missing_count = expected_count - (len(forecast_columns) + len(missing_columns))
                suggested_columns = self.suggest_future_columns(forecast_columns[-1], missing_count)
                for column in suggested_columns:
                    errors.append(f"Missing forecast column: {column}")

        return errors

    def validate_forecast_with_historical(self, future_df: pd.DataFrame, historical_df: pd.DataFrame) -> list:
        """Validate that future forecast columns follow historical data columns."""
        historical_columns = self.extract_forecast_columns(historical_df)
        future_columns = self.extract_forecast_columns(future_df)

        errors = []
        if not historical_columns or not future_columns:
            errors.append("One of the DataFrames does not contain valid forecast columns.")
            return errors

        last_historical_date = datetime.strptime(str(historical_columns[-1]), '%Y%m')
        expected_future_start = last_historical_date + relativedelta(months=1)

        actual_future_start = datetime.strptime(str(future_columns[0]), "%Y%m")
        if expected_future_start != actual_future_start:
            errors.append(f"Future forecast should start from {expected_future_start.strftime('%Y%m')} based on the Historical forecast")
            return errors
        else:
            return errors


    def validate_data_expression(self, df: pd.DataFrame, rules: list) -> list:
        """Check if the data in columns matches the regular expression defined in the DataExpression."""
        errors_dict = {}
        df.columns = df.columns.map(str)

        for column_info in rules:
            col_name = column_info.Name
            alt_names = column_info.AlternateNames
            data_expr = column_info.DataExpression
            common_expr = column_info.CustomExpressionError

            # Get actual column names based on the main name or alternate names
            actual_columns = [col for col in df.columns if col.replace("\n", "") == col_name or col in alt_names]

            for col in actual_columns:
                # Skip validation if common_expr is empty
                if common_expr == "":
                    continue

                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].dt.strftime('%d-%m-%Y')  # Format datetime to string

                if data_expr:
                    # Check each value against the regex
                    invalid_found = any(not self.check_regex(str(value), data_expr) for value in df[col])

                    if invalid_found:
                        # Group columns by common_expr
                        if common_expr not in errors_dict:
                            errors_dict[common_expr] = []
                        errors_dict[common_expr].append(col)

        # Format the output
        errors = []
        for common_expr, cols in errors_dict.items():
            errors.append(f"{common_expr} - {', '.join(cols)}")

        return errors if errors else []

    def validate_repeat_number(self, df: pd.DataFrame, rules: list) -> list:
        """Validate that columns follow the repeat number rules, including regex matching for NameExpression."""
        errors = []
        for column_info in rules:
            col_name = column_info.Name
            alt_names = column_info.AlternateNames
            name_exp = column_info.NameExpression
            repeat_number = column_info.RepeatNumber

            # Find columns by exact name or alternate names
            actual_columns = [col for col in df.columns if col == col_name or col in alt_names]

            # If no exact or alternate names are found, use the regex to match the columns
            if not actual_columns and not col_name and not alt_names and name_exp:
                regex = re.compile(name_exp)
                actual_columns = [col for col in df.columns if regex.match(col)]

            # Validate the number of found columns against the expected repeat number
            if repeat_number > 1 and len(actual_columns) != repeat_number:
                if col_name or alt_names:
                    column_to_use = col_name if col_name else alt_names
                    errors.append(f"Column -'{column_to_use}' should appear {repeat_number} times, but found {len(actual_columns)} times.")
                elif not col_name and not alt_names:
                    errors.append(f"Column - YearMonth should appear {repeat_number} times, but found {len(actual_columns)} times.")

        return errors

    def check_regex(self, value, pattern) -> bool:
        """Helper function to check regex pattern."""
        if pd.isnull(value) or pattern == "":
            return True  # No need to check null values or empty regex
        return bool(re.match(pattern, str(value)))