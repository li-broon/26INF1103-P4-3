from src.io_manager.constants import PAGE_SIZE


# Which page of a table is showing and moves between pages (Never Prints)
class Pager:
    def __init__(self, total_rows: int, page_size: int = PAGE_SIZE):
        self._total = total_rows     # How many rows the table has
        self._page_size = page_size  # How many rows fit on one page
        self._page = 1               # Always starts on page 1

    # The page currently shown
    def current_page(self) -> int:
        return self._page

    # How many pages the table needs (an empty table still has 1 page)
    def page_count(self) -> int:
        # Divide and round UP: -(-7 // 3) = 3, because 7 rows need 3 pages (3 + 3 + 1)
        return max(-(-self._total // self._page_size), 1)

    # The first and last row positions on the current page, e.g. (0, 3) for page 1
    def row_range(self) -> tuple:
        first = (self._page - 1) * self._page_size
        last = min(first + self._page_size, self._total)
        return first, last

    # Moves to the next page. Returns False if already on the last page
    def next(self) -> bool:
        if self._page >= self.page_count():
            return False
        self._page += 1  # The Pager now remembers it is on the next page
        return True

    # Moves to the previous page. Returns False if already on page 1
    def previous(self) -> bool:
        if self._page <= 1:
            return False
        self._page -= 1
        return True
