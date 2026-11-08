from enum import Enum

class OptimizationSense(Enum):
    MAXIMIZE = "max"
    MINIMIZE = "min"
    
class Relation(Enum):
    LESS_EQUAL = "<="
    GREAT_EQUAL = ">="
    EQUAL = "="