from src.io_manager.constants import BOLD, CYAN, RESET, UNDERLINE


#Prints One Page of the Reports Table: Title, Header, Rows with their Details, Page Footer
class ReportTableView:
    def __init__(self, formatter):
        self._formatter = formatter   # The shared ReportFormatter, handed in (association)

    def show(self, table, title: str, pager) -> None:
        total = len(table)
        first, last = pager.row_range()

        print(f"\n{BOLD}{UNDERLINE}{title}{RESET}\n")
        header = self._formatter.build_header()
        print(f"{BOLD}{header}{RESET}")
        print("-" * len(header))

        # One block per report: the summary row, then its wrapped details underneath
        rows = table.iloc[first:last].fillna("-")
        for number, report in enumerate(rows.to_dict("records"), start=first + 1):
            print(self._formatter.build_row(number, report))
            for line in self._formatter.build_details(report):
                print(line)
            print()

        print(f"\n{CYAN}Page {pager.current_page()} of {pager.page_count()}  (showing {first + 1}-{last} of {total}){RESET}\n")