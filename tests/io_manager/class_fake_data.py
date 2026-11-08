# A fake Data Manager: always returns the table it was given
class FakeData:
    def __init__(self, table):
        self._table = table

    def load_records(self, ascending=False):
        return self._table

    def get_unique_values(self, column):
        return []

    def load_matching_records(self, column, value, ascending=False):
        return self._table
