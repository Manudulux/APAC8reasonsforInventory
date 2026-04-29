from typing import List, Optional
from src.Classes.Errors import Error

class Column:
    def __init__(self,
                 Name: Optional[str] = "",
                 AlternateNames: Optional[List[str]] = [""],
                 NameExpression: Optional[str] = "",
                 DataExpression: Optional[str] = "",
                 DataType: Optional[str] = "",
                 Required: Optional[bool] = True,
                 RepeatNumber: Optional[int] = 1,
                 CustomExpressionError: Optional[str] = "",
                 Errors: Optional[List[Error]] = None):
        self.Name = Name
        self.AlternateNames = AlternateNames if AlternateNames is not None else []
        self.NameExpression = NameExpression
        self.DataExpression = DataExpression
        self.DataType = DataType
        self.Required = Required
        self.RepeatNumber = RepeatNumber
        self.CustomExpressionError = CustomExpressionError
        self.Errors = [Error(**err) for err in (Errors if Errors else [])]

    def __repr__(self):
        return f"""(Name={self.Name},
                AlternateNames={self.AlternateNames},
                NameExpression={self.NameExpression},
                DataExpression={self.DataExpression},
                DataType={self.DataType},
                Required={self.Required},
                CustomExpressionError={self.CustomExpressionError},
                RepeatNumber={self.RepeatNumber},
                Errors={self.Errors})""" 