from enum import StrEnum


class AttributeDataType(StrEnum):
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    SELECT = "select"
    MULTI_SELECT = "multi_select"