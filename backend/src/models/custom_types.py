from sqlalchemy.types import TypeDecorator, TEXT


class Vector(TypeDecorator):
    """
    Custom type for PostgreSQL's VECTOR data type using the pgvector extension.
    """

    impl = TEXT

    def __init__(self, dimension):
        self.dimension = dimension
        super(Vector, self).__init__()

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(TEXT())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return f"[{', '.join(map(str, value))}]"

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return list(map(float, value.strip("[]").split(",")))
