class DataTransferObject:
    @classmethod
    def tag_key(cls) -> str:
        return "__class__"

    @classmethod
    def tag_value(cls) -> "str | None":
        return cls.__name__


class MessageParsingError(Exception):
    pass