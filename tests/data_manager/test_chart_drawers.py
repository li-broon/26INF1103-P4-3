import matplotlib
matplotlib.use("agg")  # Draw to memory: no screen is needed (CI and the Docker test command have none)
import matplotlib.pyplot as plt
import pandas as pd

from src.data_manager.charts.chart_drawer import ChartDrawer
from src.data_manager.charts.default_charts import create_default_charts
from src.data_manager.charts.language_chart import LanguageChart
from src.data_manager.charts.location_chart import LocationChart
from src.data_manager.charts.monthly_chart import MonthlyChart
from src.data_manager.charts.root_cause_chart import RootCauseChart
from src.data_manager.charts.severity_by_cause_chart import SeverityByCauseChart
from src.data_manager.charts.time_chart_drawer import TimeChartDrawer
from src.data_manager.constants import MAX_LABEL_LENGTH, MONTH_NAMES, OTHER_LABEL, TOP_LOCATIONS

# What a worker could not answer is stored like this
UNKNOWN = "unknown (worker could not say)"


# One report with every column the charts use (change anything with keyword arguments)
def report(**changes):
    row = {"reporter_name": "Ann", "incident_date": "2026-10-01", "importance_score": 5, "location": "Tuas, bay 2",
           "root_cause_category": "Fire", "detected_language": "English", "ai_severity": "High", "work_stoppage_hours": 1}
    row.update(changes)
    return row

# A table of reports; each item of changes is the keyword arguments of one report
def table_of(*changes):
    return pd.DataFrame([report(**change) for change in changes])

# Draws a chart on a fresh figure. Returns (True or False as the chart answered, the figure)
def draw(chart, table):
    figure = plt.figure(figsize=(10, 6), layout="constrained")
    return chart.draw(figure.add_subplot(), table), figure

# The axes (not the colour bars) of the figure with this title
def axis_titled(figure, title):
    return next(ax for ax in figure.axes if ax.get_title() == title)

# The text of each legend entry of an axis, in order
def legend_labels(ax):
    return [text.get_text() for text in ax.get_legend().get_texts()]

# The text of each x tick label of an axis (major ticks, or the year labels when minor is True)
def x_labels(ax, minor=False):
    return [label.get_text() for label in ax.get_xticklabels(minor=minor)]

# Each bar of an axis as (month position on the x axis, bottom, height), skipping bars with no height
def bars(ax):
    return [(round(bar.get_x() + bar.get_width() / 2), round(bar.get_y(), 2), round(bar.get_height(), 2))
            for bar in ax.patches if bar.get_height() > 0]

# A table that has every column the charts use, but nothing a chart could draw (no valid date, blank and unknown answers)
def unusable_table():
    return table_of({"incident_date": "not a date", "location": "", "root_cause_category": UNKNOWN,
                     "detected_language": float("nan"), "ai_severity": ""})


# The menu shows the five charts in this order, each under the name the user types
def test_default_charts_are_the_five_charts_in_menu_order():
    charts = create_default_charts()
    assert list(charts) == ["root_cause", "language", "monthly", "location", "severity_by_cause"]
    assert all(key == chart.key for key, chart in charts.items())

# Every chart has its own menu text, so the menu never shows two lines alike
def test_default_charts_have_different_titles():
    titles = [chart.title for chart in create_default_charts().values()]
    assert all(title.strip() for title in titles)
    assert len(set(titles)) == len(titles)

# Every chart draws normal reports without a crash and says it drew something
def test_every_default_chart_draws_normal_reports():
    table = table_of({}, {"incident_date": "2026-11-05", "root_cause_category": "Electrical", "location": "Jurong"},
                     {"incident_date": "2025-03-12", "ai_severity": "Low", "detected_language": "Tamil"})
    for key, chart in create_default_charts().items():
        drew, figure = draw(chart, table)
        assert drew is True, key
        plt.close(figure)

# A table without one of the chart's columns gives "nothing to draw" for every chart, not a KeyError
def test_every_default_chart_says_no_data_when_a_column_is_missing():
    for key, chart in create_default_charts().items():
        drew, figure = draw(chart, pd.DataFrame([{"reporter_name": "Ann"}]))
        assert drew is False, key
        plt.close(figure)

# Reports whose chart values are all blank, unknown or not a date give "nothing to draw" for every chart
def test_every_default_chart_says_no_data_when_nothing_is_usable():
    for key, chart in create_default_charts().items():
        drew, figure = draw(chart, unusable_table())
        assert drew is False, key
        plt.close(figure)


# A chart that only remembers whether it was asked to draw
class SpyChart(ChartDrawer):
    def __init__(self, **options):
        super().__init__("spy", "Spy chart", **options)
        self.drawn = False

    def _draw(self, ax, table):
        self.drawn = True
        return True

# A chart is only drawn when the table has all the columns it needs; otherwise it answers False without trying
def test_chart_is_not_drawn_when_a_required_column_is_missing():
    chart = SpyChart(required_columns=("location", "ai_severity"))
    assert chart.draw(None, pd.DataFrame([{"location": "Tuas"}])) is False
    assert chart.drawn is False
    assert chart.draw(None, pd.DataFrame([{"location": "Tuas", "ai_severity": "Low"}])) is True
    assert chart.drawn is True

# A chart with one panel needs 1 unit of room, one with 3 panels needs 3, and an explicit height wins over the panels
def test_chart_height_follows_panels_unless_given():
    assert SpyChart().panels == 1 and SpyChart().height == 1.0
    assert SpyChart(panels=3).panels == 3 and SpyChart(panels=3).height == 3.0
    assert SpyChart(panels=3, height=0.8).height == 0.8

# Blanks, NaN and "unknown ..." answers (any case) become missing; other text is trimmed
def test_known_values_blank_out_unknown_answers():
    table = pd.DataFrame({"cause": ["  Fire ", "", "   ", float("nan"), UNKNOWN, "UNKNOWN", "Unknown", "Electrical"]})
    cleaned = ChartDrawer._known_values(table, "cause").tolist()
    assert cleaned[0] == "Fire" and cleaned[-1] == "Electrical"
    assert all(pd.isna(value) for value in cleaned[1:-1])

# Counting values leaves out the same blanks and unknowns, and lists the most common value first
def test_count_values_skips_unknown_answers_and_sorts_by_count():
    table = pd.DataFrame({"cause": ["Fire", "Water", "Water", " Water ", "", float("nan"), UNKNOWN, "Unknown"]})
    counts = ChartDrawer._count_values(table, "cause")
    assert counts.to_dict() == {"Water": 3, "Fire": 1}
    assert counts.index[0] == "Water"

# There is one colour per name, and a long list of names gets the bigger palette and starts again after it runs out
def test_palette_gives_one_colour_per_name():
    assert len(ChartDrawer._palette(4)) == 4
    assert len(set(ChartDrawer._palette(10))) == 10
    assert len(set(ChartDrawer._palette(20))) == 20
    colours = ChartDrawer._palette(25)
    assert len(colours) == 25 and colours[20] == colours[0]

# One panel is the axis itself; three panels replace it with three new axes
def test_split_axes_gives_the_axis_back_or_cuts_it_into_panels():
    figure = plt.figure(layout="constrained")
    ax = figure.add_subplot()
    assert ChartDrawer._split_axes(ax, 1) == [ax]
    assert len(figure.axes) == 1

    panels = ChartDrawer._split_axes(ax, 3)
    assert len(panels) == 3 and ax not in figure.axes
    assert len(figure.axes) == 3
    plt.close(figure)


# Reports with a missing, unreadable or wrongly written date are left out; the others get the month they happened in
def test_dated_keeps_only_valid_dates_and_adds_their_month():
    table = pd.DataFrame({"incident_date": ["2026-10-01", "2026-10-30", "2025-03-12", "not a date", "", float("nan"),
                                            "01/10/2026", "2026-13-01"]})
    data = TimeChartDrawer._dated(table)
    assert data["_month"].astype(str).tolist() == ["2026-10", "2026-10", "2025-03"]

# The months run from January of the first year to December of the last, so every year shows all 12 months
def test_month_range_covers_whole_years():
    months = TimeChartDrawer._month_range(pd.Series(pd.PeriodIndex(["2025-03", "2026-10"], freq="M")))
    assert len(months) == 24
    assert str(months[0]) == "2025-01" and str(months[-1]) == "2026-12"

# The month axis has a tick for every month, each year is written once under its months, and a dashed line separates years
def test_mark_months_labels_months_and_years():
    figure = plt.figure()
    ax = figure.add_subplot()
    TimeChartDrawer._mark_months(ax, pd.period_range("2025-01", "2026-12", freq="M"))
    assert x_labels(ax) == MONTH_NAMES * 2
    assert x_labels(ax, minor=True) == ["2025", "2026"]
    assert len(ax.lines) == 1 and ax.lines[0].get_linestyle() == "--"  # One line, between the two years
    plt.close(figure)


# The pie's legend names each language with how many reports and what share, most common first
def test_language_chart_counts_each_language():
    table = table_of({}, {}, {}, {"detected_language": "Tamil"})
    drew, figure = draw(LanguageChart(), table)
    assert drew is True
    ax = figure.axes[0]
    assert legend_labels(ax) == ["English: 3 (75%)", "Tamil: 1 (25%)"]
    assert ax.get_title() == LanguageChart().title
    assert len(ax.patches) == 2  # One wedge per language
    plt.close(figure)

# Blank, missing and unknown languages are not a wedge
def test_language_chart_ignores_unknown_languages():
    table = table_of({}, {"detected_language": ""}, {"detected_language": UNKNOWN}, {"detected_language": float("nan")})
    drew, figure = draw(LanguageChart(), table)
    assert drew is True
    assert legend_labels(figure.axes[0]) == ["English: 1 (100%)"]
    plt.close(figure)

# With no known language at all there is nothing to draw
def test_language_chart_has_nothing_to_draw_without_a_known_language():
    for languages in ([""], [UNKNOWN], [float("nan")], ["", UNKNOWN]):
        drew, figure = draw(LanguageChart(), pd.DataFrame({"detected_language": languages}))
        assert drew is False, languages
        plt.close(figure)


# One stacked bar per month: the most common cause at the bottom, and the month's total written on top
def test_root_cause_chart_stacks_causes_per_month():
    table = table_of({}, {}, {"root_cause_category": "Electrical"}, {"incident_date": "2026-11-20"})
    drew, figure = draw(RootCauseChart(), table)
    assert drew is True
    ax = figure.axes[0]
    # October (position 9): Fire twice, with Electrical on top of it; November (position 10): Fire once
    assert sorted(bars(ax)) == [(9, 0.0, 2.0), (9, 2.0, 1.0), (10, 0.0, 1.0)]
    assert legend_labels(ax) == ["Fire", "Electrical"]
    assert sorted(text.get_text() for text in ax.texts) == ["1", "3"]
    plt.close(figure)

# A year always shows all 12 months, from January to December, labelled with the year
def test_root_cause_chart_shows_every_month_of_the_year():
    drew, figure = draw(RootCauseChart(), table_of({}))
    ax = figure.axes[0]
    assert x_labels(ax) == MONTH_NAMES
    assert x_labels(ax, minor=True) == ["2026"]
    plt.close(figure)

# Reports from two years share one axis of 24 months, and each report lands in its own year
def test_root_cause_chart_spans_several_years():
    drew, figure = draw(RootCauseChart(), table_of({"incident_date": "2025-03-12"}, {}))
    ax = figure.axes[0]
    assert x_labels(ax) == MONTH_NAMES * 2
    assert x_labels(ax, minor=True) == ["2025", "2026"]
    assert sorted(position for position, _, _ in bars(ax)) == [2, 21]  # March 2025 and October 2026
    plt.close(figure)

# A report with an unreadable date or an unknown cause is left out rather than breaking the chart
def test_root_cause_chart_skips_reports_it_cannot_place():
    table = table_of({}, {"incident_date": "not a date"}, {"incident_date": ""}, {"root_cause_category": UNKNOWN},
                     {"root_cause_category": ""}, {"root_cause_category": float("nan")})
    drew, figure = draw(RootCauseChart(), table)
    assert drew is True
    assert sum(height for _, _, height in bars(figure.axes[0])) == 1
    plt.close(figure)

# With no report that has both a valid date and a known cause there is nothing to draw
def test_root_cause_chart_has_nothing_to_draw_without_usable_reports():
    for table in (unusable_table(), table_of({"incident_date": "soon"}), table_of({"root_cause_category": UNKNOWN})):
        drew, figure = draw(RootCauseChart(), table)
        assert drew is False
        plt.close(figure)


# One line per year: the legend gives each year's total, and each line has the counts of its months
def test_monthly_chart_draws_one_line_per_year():
    table = table_of({"incident_date": "2025-01-10"}, {"incident_date": "2025-01-20"},
                     {"incident_date": "2026-01-05"}, {"incident_date": "2026-03-05"}, {"incident_date": "2026-03-06"})
    drew, figure = draw(MonthlyChart(), table)
    assert drew is True
    ax = figure.axes[0]
    assert legend_labels(ax) == ["2025 (2 incidents)", "2026 (3 incidents)"]
    assert ax.lines[0].get_ydata().tolist()[:3] == [2, 0, 0]
    assert ax.lines[1].get_ydata().tolist() == [1, 0, 2]
    assert x_labels(ax) == MONTH_NAMES
    plt.close(figure)

# Earlier years are drawn to December, but the latest year stops at its last month so the empty months do not look like 0 incidents
def test_monthly_chart_stops_the_latest_year_at_its_last_month():
    table = table_of({"incident_date": "2025-02-01"}, {"incident_date": "2026-10-01"})
    drew, figure = draw(MonthlyChart(), table)
    ax = figure.axes[0]
    assert len(ax.lines[0].get_xdata()) == 12
    assert len(ax.lines[1].get_xdata()) == 10
    plt.close(figure)

# The axis leaves room above the highest point
def test_monthly_chart_leaves_room_above_the_highest_month():
    drew, figure = draw(MonthlyChart(), table_of({}, {}, {}))
    assert figure.axes[0].get_ylim() == (0, 4)  # 3 incidents in the busiest month, plus one
    plt.close(figure)

# Reports without a valid date are not counted
def test_monthly_chart_ignores_reports_without_a_valid_date():
    drew, figure = draw(MonthlyChart(), table_of({}, {"incident_date": "not a date"}, {"incident_date": ""}))
    assert drew is True
    assert legend_labels(figure.axes[0]) == ["2026 (1 incidents)"]
    plt.close(figure)

# With no valid date at all there is nothing to draw
def test_monthly_chart_has_nothing_to_draw_without_a_valid_date():
    drew, figure = draw(MonthlyChart(), table_of({"incident_date": "not a date"}, {"incident_date": ""}))
    assert drew is False
    plt.close(figure)


# The chart has two panels, per month and per year, in place of the one axis it was given
def test_location_chart_has_a_monthly_and_a_yearly_panel():
    drew, figure = draw(LocationChart(), table_of({}, {"location": "Jurong"}))
    assert drew is True
    assert [ax.get_title() for ax in figure.axes] == ["Incidents per month, by location", "Incidents per year, by location"]
    assert sorted(legend_labels(figure.axes[0])) == ["Jurong", "Tuas, bay 2"]
    plt.close(figure)

# Names longer than the limit are shortened with "..." so the legend stays readable; short names are kept as they are
def test_location_chart_shortens_long_names():
    long_name = "Block 7 Ubi Industrial Park Loading Bay Number 12"
    assert len(long_name) > MAX_LABEL_LENGTH
    drew, figure = draw(LocationChart(), table_of({"location": long_name}, {"location": "Jurong"}))
    labels = legend_labels(figure.axes[0])
    assert long_name[:MAX_LABEL_LENGTH - 3] + "..." in labels
    assert "Jurong" in labels
    assert all(len(label) <= MAX_LABEL_LENGTH for label in labels)
    plt.close(figure)

# Only the TOP_LOCATIONS busiest places are named; every other place is grouped as "Other" and still counted
def test_location_chart_groups_the_other_places():
    places = [f"Place {number}" for number in range(TOP_LOCATIONS + 2)]
    table = table_of(*[{"location": place} for place in places])
    drew, figure = draw(LocationChart(), table)
    labels = legend_labels(figure.axes[0])
    assert len(labels) == TOP_LOCATIONS + 1
    assert OTHER_LABEL in labels
    assert sum(height for _, _, height in bars(figure.axes[0])) == len(places)  # No report is lost
    plt.close(figure)

# With few places there is no "Other"
def test_location_chart_has_no_other_group_when_every_place_is_shown():
    drew, figure = draw(LocationChart(), table_of(*[{"location": f"Place {number}"} for number in range(TOP_LOCATIONS)]))
    assert OTHER_LABEL not in legend_labels(figure.axes[0])
    plt.close(figure)

# A report with no known location or no valid date is left out
def test_location_chart_skips_reports_it_cannot_place():
    table = table_of({}, {"location": ""}, {"location": UNKNOWN}, {"location": float("nan")}, {"incident_date": "not a date"})
    drew, figure = draw(LocationChart(), table)
    assert drew is True
    assert sum(height for _, _, height in bars(figure.axes[0])) == 1
    plt.close(figure)

# The yearly panel has one group of bars per year
def test_location_chart_yearly_panel_has_a_bar_group_per_year():
    drew, figure = draw(LocationChart(), table_of({"incident_date": "2025-05-01"}, {}, {}))
    yearly = figure.axes[1]
    assert legend_labels(yearly) == ["2025", "2026"]
    assert [bar.get_width() for container in yearly.containers for bar in container] == [1, 2]
    plt.close(figure)

# With no report that has both a valid date and a known location there is nothing to draw
def test_location_chart_has_nothing_to_draw_without_usable_reports():
    for table in (unusable_table(), table_of({"location": UNKNOWN}), table_of({"incident_date": "soon"})):
        drew, figure = draw(LocationChart(), table)
        assert drew is False
        plt.close(figure)


# Severity becomes a number whatever the capital letters; a blank or unknown level has no number
def test_severity_score_turns_levels_into_numbers():
    score = SeverityByCauseChart._severity_score
    assert [score(level) for level in ("Low", "Medium", "High", "Critical")] == [1, 2, 3, 4]
    assert [score(level) for level in ("low", "HIGH", "cRiTiCaL")] == [1, 3, 4]
    assert score(None) is None and score(float("nan")) is None
    assert score(UNKNOWN) is None and score("Severe") is None

# Electrical: Critical, Critical, High (mean 3.67, median 4); Fire: High, Low (mean 2, median 2)
def severity_table():
    return table_of({"root_cause_category": "Electrical", "ai_severity": "Critical"},
                    {"root_cause_category": "Electrical", "ai_severity": "Critical"},
                    {"root_cause_category": "Electrical", "ai_severity": "High"},
                    {"ai_severity": "High"}, {"ai_severity": "Low"})

# The chart has three panels: the yearly bars, and a heat map each for the mean and the median
def test_severity_chart_has_three_panels():
    drew, figure = draw(SeverityByCauseChart(), severity_table())
    assert drew is True
    titles = [ax.get_title() for ax in figure.axes]
    assert titles[:3] == ["Mean (bars) and median (diamonds) severity per year", "Mean severity per month",
                          "Median severity per month"]
    plt.close(figure)

# Each cause gets a bar at its mean severity and a diamond at its median, the most severe cause first
def test_severity_chart_yearly_panel_shows_mean_and_median():
    drew, figure = draw(SeverityByCauseChart(), severity_table())
    yearly = axis_titled(figure, "Mean (bars) and median (diamonds) severity per year")
    assert x_labels(yearly) == ["Electrical", "Fire"]
    assert [round(bar.get_height(), 2) for bar in yearly.patches[:2]] == [3.67, 2.0]
    assert [round(float(y), 2) for _, y in yearly.collections[0].get_offsets()] == [4.0, 2.0]
    assert sorted(legend_labels(yearly)) == ["2026 mean", "Median"]  # Matplotlib decides the order
    plt.close(figure)

# Reports from two years get a group of bars per year in each cause
def test_severity_chart_yearly_panel_has_a_bar_per_year():
    table = table_of({"incident_date": "2025-04-01", "ai_severity": "Low"}, {"ai_severity": "Critical"})
    drew, figure = draw(SeverityByCauseChart(), table)
    yearly = axis_titled(figure, "Mean (bars) and median (diamonds) severity per year")
    assert sorted(legend_labels(yearly)) == ["2025 mean", "2026 mean", "Median"]
    assert [round(bar.get_height(), 2) for bar in yearly.patches[:2]] == [1.0, 4.0]
    plt.close(figure)

# The heat maps have a row per cause and a column per month; months with no incident are left empty, the rest hold the number
def test_severity_chart_heat_maps_hold_mean_and_median_per_month():
    drew, figure = draw(SeverityByCauseChart(), severity_table())
    for title, electrical, fire in (("Mean severity per month", 3.67, 2.0), ("Median severity per month", 4.0, 2.0)):
        values = axis_titled(figure, title).images[0].get_array()
        assert values.shape == (2, 12)  # Electrical and Fire, January to December
        assert round(float(values[0, 9]), 2) == electrical  # October
        assert round(float(values[1, 9]), 2) == fire
        assert values.mask[0, 0] and values.mask[1, 11]     # No incident in January or December
    plt.close(figure)

# Each filled cell has its number written in it
def test_severity_chart_heat_map_cells_show_their_number():
    drew, figure = draw(SeverityByCauseChart(), severity_table())
    cells = sorted(text.get_text() for text in axis_titled(figure, "Mean severity per month").texts)
    assert cells == ["2.0", "3.7"]
    plt.close(figure)

# Severity is matched whatever the capital letters, and a report with an unknown severity or cause is left out
def test_severity_chart_skips_reports_it_cannot_score():
    table = table_of({"ai_severity": "critical"}, {"ai_severity": UNKNOWN}, {"ai_severity": ""}, {"ai_severity": float("nan")},
                     {"root_cause_category": "Water", "ai_severity": "Severe"}, {"root_cause_category": UNKNOWN},
                     {"incident_date": "not a date"})
    drew, figure = draw(SeverityByCauseChart(), table)
    assert drew is True
    yearly = axis_titled(figure, "Mean (bars) and median (diamonds) severity per year")
    assert x_labels(yearly) == ["Fire"]  # Water's only severity is not a level, so Water is not shown
    assert [round(bar.get_height(), 2) for bar in yearly.patches[:1]] == [4.0]
    plt.close(figure)

# With no report that has a valid date, a known cause and a known severity there is nothing to draw
def test_severity_chart_has_nothing_to_draw_without_usable_reports():
    for table in (unusable_table(), table_of({"ai_severity": UNKNOWN}), table_of({"ai_severity": float("nan")}),
                  table_of({"root_cause_category": ""}), table_of({"incident_date": "soon"})):
        drew, figure = draw(SeverityByCauseChart(), table)
        assert drew is False
        plt.close(figure)
