import pandas as pd

from src.data_manager.charts.chart_drawer import ChartDrawer

class LanguageChart(ChartDrawer):

    def __init__(self) -> None:
        super().__init__("language", "Languages reports were made in", ("detected_language",), height=0.8)  # A pie needs less room than a bar chart

    def _draw(self, ax, table: pd.DataFrame) -> bool:
        counts = self._count_values(table, "detected_language")
        if counts.empty:
            return False
        wedges, _ = ax.pie(counts.values, startangle=90, colors=self._palette(len(counts)))
        total = counts.sum()
        entries = [f"{language}: {count} ({count / total:.0%})" for language, count in counts.items()]
        ax.legend(wedges, entries, title="Language", fontsize=8, title_fontsize=8, loc="center left", bbox_to_anchor=(1.5, 0.5))
        ax.set_title(self._title)
        return True