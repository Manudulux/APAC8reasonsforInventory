from typing import List, Optional
from src.Classes.Errors import Error
from src.Classes.Columns import Column

class Sheet:
    def __init__(self,
                 Name: Optional[str] = None,
                 NameExpression: Optional[str] = None,
                 Variable: Optional[str] = None,
                 Columns: Optional[List[Column]] = None,
                 Errors: Optional[List[Error]] = None,
                 Data: Optional[str] = None,
                 FileName: Optional[str] = None):
        self.Name = Name
        self.NameExpression = NameExpression
        self.Variable = Variable
        self.Columns = Columns if Columns is not None else []
        self.Errors = [Error(**err) for err in (Errors if Errors else [])]
        self.Data = Data
        self.FileName = FileName

    def __repr__(self):
        return f"""Sheet(Name={self.Name},
                        NameExpression={self.NameExpression},
                        Columns={self.Columns},
                        Variable={self.Variable},
                        Errors={self.Errors},
                        Data={self.Data},
                        FileName={self.FileName})"""
