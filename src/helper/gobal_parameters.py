import json
from src.helper import GLOBAL_CONFIG, update_global_config

class global_parameter_class:
    def __init__(self) -> None:
        pass

    def validate_global_config(self, data):
        try:
            errors = {}
            if not isinstance(data.get("global_parameters"), list) or len(data["global_parameters"]) == 0:
                return False, ["global_parameters should be a non-empty list"]
            params = data["global_parameters"][0]
            if params.get("forecast", {}).get("weekly_split_method") not in [0, 1]:
                errors.setdefault("weekly_split_method", []).append("can only be 0 or 1")
            if params.get("forecast", {}).get("demand_variation_method") not in ["Under", "Both"]:
                errors.setdefault("demand_variation_method", []).append("can only be 'Under' or 'Both'")
            variance_errors = []
            for key, value in params.get("rm_segmentation", {}).get("variance", {}).items():
                if not isinstance(value, list) or len(value) != 2 or not all(isinstance(x, int) for x in value):
                    errors.setdefault(f"Variance key {key}", []).append("must be a list of two integers")
                elif not (0 <= value[0] <= value[1] <= 100):
                    variance_errors.append(key)
            if variance_errors:
                errors["variance"] = [f"keys {variance_errors} must be in the range 0-100"]
            segment_errors = []
            for key, value in params.get("rm_segmentation", {}).get("segment", {}).items():
                if not isinstance(value, list) or len(value) != 2 or not all(isinstance(x, int) for x in value):
                    errors.setdefault(f"Segment key {key}", []).append("must be a list of two integers")
                elif not (0 <= value[0] <= value[1] <= 100):
                    segment_errors.append(key)
            if segment_errors:
                errors["segment"] = [f"keys {segment_errors} must be in the range 0-100"]
            service_level_errors = []
            for key, value in params.get("service_level_mapping", {}).items():
                if not isinstance(value, int) or value >= 100:
                    service_level_errors.append(key)
            if service_level_errors:
                errors["service_level_mapping"] = [f"keys {service_level_errors} must be less than 100"]
            production_day_errors = []
            for key, value in params.get("production_days", {}).items():
                if not isinstance(value, int) or value > 31:
                    production_day_errors.append(key)
            if production_day_errors:
                errors["production_days"] = [f"keys {production_day_errors} cannot be greater than 31"]
            final_errors = [f"{k.replace('_',' ')} {m}" for k, msgs in errors.items() for m in msgs]
            if final_errors:
                return False, final_errors
            return True, "Validation passed"
        except Exception as e:
            return str(e)

    def update_global_config(self, valid_global_params):
        try:
            update_global_config(valid_global_params)
            return "Global Parameters Updated Successfully"
        except Exception as e:
            return f"Error updating global config: {str(e)}"

    def get_global_config(self) -> dict:
        return GLOBAL_CONFIG
