from src.io_manager.constants import PAGE_SIZE

class Pager:
    def __init__(self, total_rows: int, page_size: int =PAGE_SIZE):
        self._total = total_rows #How many rows the table has
        self._page_size = page_size # How many rows fit on one page 
        self._page = 1 #Ensure the page starts at 1

    #the page currently shown 
    def current_page(self) -> int:
        return self._page 

    #How many pages the table needs so the table still has 1 empty table
    def page_count(self) -> int:
        # Divide and round UP: -(-7 // 3) = 3, because 7 rows need 3 pages (3 + 3 + 1)
        return max(-(-self._total//self._page_size), 1)

    # The first and last row positions on the current page, e.g. (0, 3) for page 1
    def row_range(self) -> tuple:
        first = (self._page - 1) * self._page_size
        last = min(first + self._page_size, self._total)
        return first, last

    #Moves to the next page, Return flase if already on the last page
    def next(self) -> bool:
        if self._page >= self.page_count():
            return False
        self._page += 1 #the Pager now remembers it's on the next page
        return True

    #Moves to the previous page. return false if already on Page 1
    def previous(self) -> bool:
        if self._page <=1:
            return False
        self._page -= 1
        return True
