import json
from typing import List, Optional

class Error:
    def __init__(self, Code: Optional[int] = None, Description: Optional[str] = None):
        self.Code = Code
        self.Description = Description

    def __repr__(self):
        return f"Error(Code={self.Code}, Description={self.Description})"