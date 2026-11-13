#A fake Chart Manager: offers two charts and remembers which ones it was asked to show (nothing is drawn)
class FakeCharts:
    def __init__(self, result=None):
        #Every (chart name, save path) it was asked for, so a test can check it
        self.shown = []       
        #What show_chart should answer; None means "it worked"    
        self._result = result     

    def get_chart_options(self):
        return [("root_cause", "Incidents by root cause"), ("language", "Languages reports were made in")]

    def show_chart(self, chart_name, filter_column=None, filter_value=None, save_path=None):
        self.shown.append((chart_name, save_path))
        if self._result is not None:
            return self._result
        return True, (f"Chart saved to {save_path}" if save_path else "Chart closed.")