import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import microdf as mdf
import os
import us
import components as cmp
from components import make_html_label, make_dropdown_options

# ---------------------------------------------------------------------------- #
#                       SECTION import pre-processed data                      #
# ---------------------------------------------------------------------------- #
# Import data from Ipums
person = pd.read_csv("person.csv.gz")
spmu = pd.read_csv("spmu.csv.gz")
# import baseline poverty gap, gini by state & us
all_state_stats = pd.read_csv("all_state_stats.csv.gz", index_col=0)
# import baseline white/black/child etc. poverty rates & population
demog_stats = pd.read_csv("demog_stats.csv.gz")

# Colors
BLUE = "#1976D2"

# create a list of all states, including "US" as a state
states_no_us = person.state.unique().tolist()
states_no_us.sort()
states = ["US"] + states_no_us

# ---------------------------------------------------------------------------- #
#                            SECTION dash components                           #
# ---------------------------------------------------------------------------- #


# ----------------------- SECTION Create 4 input cards ----------------------- #
cards = dbc.CardDeck(
    [
        # -------------- SECTION Card 1 state-dropdown component ------------- #
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        # TODO create function for the HTML labels, it repeats 6 times
                        make_html_label("Select state:"),
                        dcc.Dropdown(
                            # define component_id for input of app@callback function
                            id="state-dropdown",
                            multi=False,
                            value="US",
                            # create a list of dicts of states and their labels
                            # to be selected by user in dropdown
                            options=[{"label": x, "value": x} for x in states],
                        ),
                        html.Br(),
                        make_html_label("Reform level:"),
                        dcc.RadioItems(
                            id="level",
                            options=make_dropdown_options(
                                {"Federal": "federal", "State": "state"}
                            ),
                            value="federal",
                            labelStyle={"display": "block"},
                        ),
                    ]
                ),
            ],
            color="info",
            outline=False,
        ),
        # -------------------- SECTION Card 2 - taxes ------------------- #
        # tax slider
        #   allows user to repeal certain federal and state taxes
        #   component_id: "taxes-checklist"
        # tax rate slider
        #   Allows user to adjust tax rate that determines ubi benefit amount
        #   component_id="agi-slider"
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        # define attributes of taxes-checklist component
                        make_html_label("Repeal current taxes:"),
                        html.Br(),
                        dcc.Checklist(
                            # define component id to be used in callback
                            id="taxes-checklist",
                            options=[
                                {"label": "Income taxes", "value": "fedtaxac"},
                                {
                                    "label": "Employee side payroll",
                                    "value": "fica",
                                },
                            ],
                            value=[],
                            labelStyle={"display": "block"},
                        ),
                        html.Br(),
                        # defines label/other HTML attributes of agi-slider component
                        make_html_label("Income tax rate:"),
                        dcc.Slider(
                            id="agi-slider",
                            min=0,
                            max=50,
                            step=1,
                            value=0,
                            tooltip={
                                "always_visible": True,
                                "placement": "bottom",
                            },
                            # define marker values to show increments on slider
                            marks={
                                0: {
                                    "label": "0%",
                                    "style": {"color": "#F8F8FF"},
                                },
                                10: {
                                    "style": {"color": "#F8F8FF"},
                                },
                                20: {
                                    "style": {"color": "#F8F8FF"},
                                },
                                30: {
                                    "style": {"color": "#F8F8FF"},
                                },
                                40: {
                                    "style": {"color": "#F8F8FF"},
                                },
                                50: {
                                    "label": "50%",
                                    "style": {"color": "#F8F8FF"},
                                },
                            },
                        ),
                        html.Div(id="slider-output-container"),
                    ]
                ),
                html.Br(),
            ],
            color="info",
            outline=False,
        ),
        # ----------------- SECTION Card 3 - Repeal Benefits ----------------- #
        # define third card where the repeal benefits checklist is displayed
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        # label the card
                        make_html_label("Repeal benefits:"),
                        # use  dash component to create checklist to choose
                        # which benefits to repeal
                        dcc.Checklist(
                            # this id string is a dash component_id
                            # and is referenced as in input in app.callback
                            id="benefits-checklist",
                            # 'options' here refers the selections available to the user in the
                            # checklist
                            options=make_dropdown_options(
                                {
                                    "  Child Tax Credit": "ctc",
                                    "  Supplemental Security Income (SSI)": "incssi",
                                    "  SNAP (food stamps)": "spmsnap",
                                    "  Earned Income Tax Credit": "eitcred",
                                    "  Unemployment benefits": "incunemp",
                                    "  Energy subsidy (LIHEAP)": "spmheat",
                                }
                            ),
                            # do not repeal benefits by default
                            value=[],
                            labelStyle={"display": "block"},
                        ),
                    ]
                ),
            ],
            color="info",
            outline=False,
        ),
        # exclude/include from UBI checklist
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        make_html_label("Include in UBI:"),
                        dcc.Checklist(
                            id="include-checklist",
                            options=make_dropdown_options(
                                {
                                    "non-Citizens": "non_citizens",
                                    "Children": "children",
                                    "Adult": "adults",
                                }
                            ),
                            # specify checked items
                            value=[
                                "adults",
                                "children",
                                "non_citizens",
                            ],
                            labelStyle={"display": "block"},
                        ),
                    ]
                ),
            ],
            color="info",
            outline=False,
        ),
    ]
)

# create the 2 cards the charts will go into
charts = dbc.CardDeck(
    [
        dbc.Card(
            dcc.Graph(id="my-graph", figure={}),
            body=True,
            color="info",
        ),
        dbc.Card(
            dcc.Graph(id="my-graph2", figure={}),
            body=True,
            color="info",
        ),
    ]
)
# ------------------------------- summary card ------------------------------- #
# create the summary card that contains ubi amount, revenue, pct. better off
def make_div(div_id):
    """assign html.Div to summary card"""
    div = html.Div(
        id=div_id,
        style={
            "text-align": "left",
            "color": "black",
            "fontSize": 25,
        },
    )

    return div


summary_outputs = [
    "revenue-output",  # Funds for UBI
    "ubi-population-output",  # UBI Population
    "ubi-output",  # Monthly UBI
    "winners-output",  # Percent better off
    "resources-output",  # Average change in resources per person
]

text = (
    dbc.Card(
        [
            dbc.CardBody([make_div(x) for x in summary_outputs]),
        ],
        color="white",
        outline=False,
    ),
)

# ---------------------------------------------------------------------------- #
#                              SECTION app                                     #
# ---------------------------------------------------------------------------- #

# Get base pathname from an environment variable that CS will provide.
url_base_pathname = os.environ.get("URL_BASE_PATHNAME", "/")

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.FLATLY,
        "https://fonts.googleapis.com/css2?family=Lato:wght@300;400&display=swap",
        "/assets/style.css",
    ],
    # Pass the url base pathname to Dash.
    url_base_pathname=url_base_pathname,
)

server = app.server

# Design the app
app.layout = html.Div(
    [
        # navbar
        dbc.Navbar(
            [
                html.A(
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Img(
                                    src="https://blog.ubicenter.org/_static/ubi_center_logo_wide_blue.png",
                                    height="30px",
                                )
                            ),
                        ],
                        align="center",
                        no_gutters=True,
                    ),
                    href="https://www.ubicenter.org",
                    target="blank",
                ),
                dbc.NavbarToggler(id="navbar-toggler"),
            ]
        ),
        html.Br(),
        dbc.Row(
            [
                dbc.Col(
                    html.H1(
                        "Explore funding mechanisms of UBI",
                        id="header",
                        style={
                            "text-align": "center",
                            "color": "#1976D2",
                            "fontSize": 50,
                            "letter-spacing": "2px",
                            "font-weight": 300,
                        },
                    ),
                    width={"size": 8, "offset": 2},
                ),
            ]
        ),
        html.Br(),
        dbc.Row(
            [
                dbc.Col(
                    html.H4(
                        "Use the interactive below to explore different funding mechanisms for a UBI and their impact. You may choose between repealing benefits or adding new taxes.  When a benefit is repealed or a new tax is added, the new revenue automatically funds a UBI to all people equally to ensure each plan is budget neutral.",
                        style={
                            "text-align": "left",
                            "color": "black",
                            "fontSize": 25,
                        },
                    ),
                    width={"size": 8, "offset": 2},
                ),
            ]
        ),
        html.Br(),
        dbc.Row([dbc.Col(cards, width={"size": 10, "offset": 1})]),
        html.Br(),
        dbc.Row(
            [
                dbc.Col(
                    html.H1(
                        "Results of your reform:",
                        style={
                            "text-align": "center",
                            "color": "#1976D2",
                            "fontSize": 30,
                        },
                    ),
                    width={"size": 8, "offset": 2},
                ),
            ]
        ),
        dbc.Row([dbc.Col(text, width={"size": 6, "offset": 3})]),
        html.Br(),
        dbc.Row([dbc.Col(charts, width={"size": 10, "offset": 1})]),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
        html.Br(),
    ]
)

# ---------------------------------------------------------------------------- #
#                           SECTION callbacks                                  #
# ---------------------------------------------------------------------------- #


@app.callback(
    Output(component_id="ubi-output", component_property="children"),
    Output(component_id="revenue-output", component_property="children"),
    Output(component_id="ubi-population-output", component_property="children"),
    Output(component_id="winners-output", component_property="children"),
    Output(component_id="resources-output", component_property="children"),
    Output(component_id="my-graph", component_property="figure"),
    Output(component_id="my-graph2", component_property="figure"),
    Input(component_id="state-dropdown", component_property="value"),
    Input(component_id="level", component_property="value"),
    Input(component_id="agi-slider", component_property="value"),
    Input(component_id="benefits-checklist", component_property="value"),
    Input(component_id="taxes-checklist", component_property="value"),
    Input(component_id="include-checklist", component_property="value"),
)

# TODO one function to translate args to params, another to run the function, another to return the output
def ubi(dropdown_state, level, agi_tax, benefits, taxes, include):
    """this does everything from microsimulation to figure creation.
        Dash does something automatically where it takes the input arguments
        in the order given in the @app.callback decorator
    Args:
        state:  takes input from callback input, component_id="state-dropdown"
        level:  component_id="level"
        agi_tax:  component_id="agi-slider"
        benefits:  component_id="benefits-checklist"
        taxes:  component_id="taxes-checklist"
        include: component_id="include-checklist"

    Returns:
        ubi_line: outputs to  "ubi-output" in @app.callback
        revenue_line: outputs to "revenue-output" in @app.callback
        ubi_population_line: outputs to "revenue-output" in @app.callback
        winners_line: outputs to "winners-output" in @app.callback
        resources_line: outputs to "resources-output" in @app.callback
        fig: outputs to "my-graph" in @app.callback
        fig2: outputs to "my-graph2" in @app.callback
    """

    # -------------------- calculations based on reform level -------------------- #
    # if the "Reform level" selected by the user is federal
    if level == "federal":
        # combine taxes and benefits checklists into one list to be used to
        #  subset spmu dataframe
        taxes_benefits = taxes + benefits
        # initialize new resources column with old resources as baseline
        spmu["new_resources"] = spmu.spmtotres
        # initialize revenue at zero
        revenue = 0

        # Calculate the new revenue and spmu resources from tax and benefit change
        for tax_benefit in taxes_benefits:
            # subtract taxes and benefits that have been changed from spm unit's resources
            spmu.new_resources -= spmu[tax_benefit]
            # add that same value to revenue
            revenue += mdf.weighted_sum(spmu, tax_benefit, "spmwt")

        # if "Income taxes" = ? and "child_tax_credit" = ?
        # in taxes/benefits checklist
        if ("fedtaxac" in taxes_benefits) & ("ctc" in taxes_benefits):
            spmu.new_resources += spmu.ctc
            revenue -= mdf.weighted_sum(spmu, "ctc", "spmwt")

        if ("fedtaxac" in taxes_benefits) & ("eitcred" in taxes_benefits):
            spmu.new_resources += spmu.eitcred
            revenue -= mdf.weighted_sum(spmu, "eitcred", "spmwt")

        # Calculate the new taxes from flat tax on AGI
        tax_rate = agi_tax / 100
        spmu["new_taxes"] = np.maximum(spmu.adjginc, 0) * tax_rate
        # subtract new taxes from new resources
        spmu.new_resources -= spmu.new_taxes
        # add new revenue when new taxes are applied on spmus, multiplied by weights
        revenue += mdf.weighted_sum(spmu, "new_taxes", "spmwt")

        # Calculate the total UBI a spmu recieves based on exclusions
        spmu["numper_ubi"] = spmu.numper

        # TODO make into linear equation on one line using array of some kind
        if "children" not in include:
            # subtract the number of children from the number of
            # people in spm unit receiving ubi benefit
            spmu["numper_ubi"] -= spmu.child

        if "non_citizens" not in include:
            spmu["numper_ubi"] -= spmu.non_citizen

        if ("children" not in include) and ("non_citizens" not in include):
            spmu["numper_ubi"] += spmu.non_citizen_child

        if "adults" not in include:
            spmu["numper_ubi"] -= spmu.adult

        if ("adults" not in include) and ("non_citizens" not in include):
            spmu["numper_ubi"] += spmu.non_citizen_adult

        # Assign UBI
        ubi_population = (spmu.numper_ubi * spmu.spmwt).sum()
        ubi_annual = revenue / ubi_population
        spmu["total_ubi"] = ubi_annual * spmu.numper_ubi

        # Calculate change in resources
        spmu.new_resources += spmu.total_ubi
        spmu["new_resources_per_person"] = spmu.new_resources / spmu.numper
        # Sort by state

        # NOTE: the "target" here refers to the population being
        # measured for gini/poverty rate/etc.
        # I.e. the total population of the state/country and
        # INCLUDING those excluding form recieving ubi payments

        # state here refers to the selection from the drop down, not the reform level
        if dropdown_state == "US":
            target_spmu = spmu
        else:
            target_spmu = spmu[spmu.state == dropdown_state]

    # if the "Reform level" dropdown selected by the user is State
    if level == "state":

        # Sort by state
        if dropdown_state == "US":
            target_spmu = spmu
        else:
            target_spmu = spmu[spmu.state == dropdown_state]

        # Initialize
        target_spmu["new_resources"] = target_spmu.spmtotres
        revenue = 0

        # Change income tax repeal to state level
        if "fedtaxac" in taxes:
            target_spmu.new_resources -= target_spmu.stataxac
            revenue += mdf.weighted_sum(target_spmu, "stataxac", "spmwt")

        # Calculate change in tax revenue
        tax_rate = agi_tax / 100
        target_spmu["new_taxes"] = target_spmu.adjginc * tax_rate

        target_spmu.new_resources -= target_spmu.new_taxes
        revenue += mdf.weighted_sum(target_spmu, "new_taxes", "spmwt")

        # Calculate the total UBI a spmu recieves based on exclusions
        target_spmu["numper_ubi"] = target_spmu.numper

        if "children" not in include:
            target_spmu["numper_ubi"] -= target_spmu.child

        if "non_citizens" not in include:
            target_spmu["numper_ubi"] -= target_spmu.non_citizen

        if ("children" not in include) and ("non_citizens" not in include):
            target_spmu["numper_ubi"] += target_spmu.non_citizen_child

        if "adults" not in include:
            target_spmu["numper_ubi"] -= target_spmu.adult

        if ("adults" not in include) and ("non_citizens" not in include):
            target_spmu["numper_ubi"] += target_spmu.non_citizen_adult

        # Assign UBI
        ubi_population = (target_spmu.numper_ubi * target_spmu.spmwt).sum()
        ubi_annual = revenue / ubi_population
        target_spmu["total_ubi"] = ubi_annual * target_spmu.numper_ubi

        # Calculate change in resources
        target_spmu.new_resources += target_spmu.total_ubi
        target_spmu["new_resources_per_person"] = (
            target_spmu.new_resources / target_spmu.numper
        )

    # NOTE: code after this applies to both reform levels

    # Merge and create target_persons -
    # NOTE: the "target" here refers to the population being
    # measured for gini/poverty rate/etc.
    # I.e. the total population of the state/country and
    # INCLUDING those excluding form recieving ubi payments
    sub_spmu = target_spmu[
        ["spmfamunit", "year", "new_resources", "new_resources_per_person"]
    ]
    target_persons = person.merge(sub_spmu, on=["spmfamunit", "year"])

    # filter demog_stats for selected state from dropdown
    baseline_demog = demog_stats[demog_stats.state == dropdown_state]

    def return_demog(demog, metric):
        """
        retrieve pre-processed data by demographic
        args:
            demog - string one of
                ['person', 'adult', 'child', 'black', 'white',
            'hispanic', 'pwd', 'non_citizen', 'non_citizen_adult',
            'non_citizen_child']
            metric - string, one of ['pov_rate', 'pop']
        returns:
            value - float
        """

        value = baseline_demog.loc[
            (baseline_demog["demog"] == demog) & (baseline_demog["metric"] == metric),
            "value",
            # NOTE: returns the first value as a float, be careful if you redefine baseline_demog
        ].values[0]

        return value

    population = return_demog(demog="person", metric="pop")
    child_population = return_demog(demog="child", metric="pop")
    non_citizen_population = return_demog(demog="non_citizen", metric="pop")
    non_citizen_child_population = return_demog(demog="non_citizen_child", metric="pop")

    # filter all state stats gini, poverty_gap, etc. for dropdown state
    baseline_all_state_stats = all_state_stats[all_state_stats.index == dropdown_state]

    def return_all_state(metric):
        """filter baseline_all_state_stats and return value of select metric

        Keyword arguments:
        metric - string, one of 'poverty_gap', 'gini', 'total_resources'

        returns:
            value- float
        """

        return baseline_all_state_stats[metric].values[0]

    # Calculate total change in resources
    original_total_resources = return_all_state("total_resources")
    # DO NOT PREPROCESS, new_resources
    new_total_resources = (target_spmu.new_resources * target_spmu.spmwt).sum()
    change_total_resources = new_total_resources - original_total_resources
    change_pp = change_total_resources / population

    original_poverty_rate = return_demog("person", "pov_rate")

    original_poverty_gap = return_all_state("poverty_gap")
    # define orignal gini coefficient
    original_gini = return_all_state("gini")

    # function to calculate rel difference between one number and another
    def rel_change(new, old, round=3):
        return ((new - old) / old).round(round)

    # Calculate poverty gap
    target_spmu["new_poverty_gap"] = np.where(
        target_spmu.new_resources < target_spmu.spmthresh,
        target_spmu.spmthresh - target_spmu.new_resources,
        0,
    )
    poverty_gap = mdf.weighted_sum(target_spmu, "new_poverty_gap", "spmwt")
    poverty_gap_change = rel_change(poverty_gap, original_poverty_gap)

    # Calculate the change in poverty rate
    target_persons["poor"] = target_persons.new_resources < target_persons.spmthresh
    total_poor = (target_persons.poor * target_persons.asecwt).sum()
    poverty_rate = total_poor / population
    poverty_rate_change = rel_change(poverty_rate, original_poverty_rate)

    # Calculate change in Gini
    gini = mdf.gini(target_persons, "new_resources_per_person", "asecwt")
    gini_change = rel_change(gini, original_gini, 3)

    # Calculate percent winners
    target_persons["winner"] = target_persons.new_resources > target_persons.spmtotres
    total_winners = (target_persons.winner * target_persons.asecwt).sum()
    percent_winners = (total_winners / population * 100).round(1)

    # -------------- calculate all of the poverty breakdown numbers -------------- #
    # Calculate the new poverty rate for each demographic
    def pv_rate(column):
        return mdf.weighted_mean(
            target_persons[target_persons[column]], "poor", "asecwt"
        )

    # Round all numbers for display in hover
    def hover_string(metric, round_by=1):
        """formats 0.121 to 12.1%"""
        string = str(round(metric * 100, round_by)) + "%"
        return string

    demogs = ["child", "adult", "pwd", "white", "black", "hispanic"]
    # create dictionary for demographic breakdown of poverty rates
    pov_breakdowns = {
        # return precomputed baseline poverty rates
        "original_rates": {demog: return_demog(demog, "pov_rate") for demog in demogs},
        "new_rates": {demog: pv_rate(demog) for demog in demogs},
    }

    # add poverty rate changes to dictionary
    pov_breakdowns["changes"] = {
        # Calculate the percent change in poverty rate for each demographic
        demog: rel_change(
            pov_breakdowns["new_rates"][demog],
            pov_breakdowns["original_rates"][demog],
        )
        for demog in demogs
    }

    # create string for hover template
    pov_breakdowns["strings"] = {
        demog: "Original "
        + demog
        + " povery rate: "
        + hover_string(pov_breakdowns["original_rates"][demog])
        + "<br><extra></extra>"
        + "New "
        + demog
        + " povery rate: "
        + hover_string(pov_breakdowns["new_rates"][demog])
        for demog in demogs
    }

    # format original and new overall poverty rate
    original_poverty_rate_string = hover_string(original_poverty_rate)
    poverty_rate_string = hover_string(poverty_rate)

    original_poverty_gap_billions = "{:,}".format(int(original_poverty_gap / 1e9))

    poverty_gap_billions = "{:,}".format(int(poverty_gap / 1e9))

    original_gini_string = str(round(original_gini, 3))
    gini_string = str(round(gini, 3))

    # --------------SECTION populates "Results of your reform:" ------------ #

    # Convert UBI and winners to string for title of chart
    ubi_string = str("{:,}".format(int(round(ubi_annual / 12))))
    winners_string = str(percent_winners)
    resources_string = "{:,}".format(int(change_pp))

    # populates Monthly UBI
    ubi_line = "Monthly UBI: $" + ubi_string

    # populates 'Funds for UBI'
    if revenue > 1e9:
        revenue_line = "Funds for UBI: $" + str((revenue / 1e9).round(1)) + " B"
    else:
        revenue_line = "Funds for UBI: $" + str((revenue / 1e6).round(1)) + " M"

    # populates revenue for UBI
    if dropdown_state != "US":
        state_spmu = target_spmu[target_spmu.state == dropdown_state]
        state_ubi_population = (state_spmu.numper_ubi * state_spmu.spmwt).sum()

        if state_ubi_population > 1e6:
            ubi_population_line = (
                "UBI Population: " + str((state_ubi_population / 1e6).round(1)) + " M"
            )
        else:
            ubi_population_line = (
                "UBI Population: " + str((state_ubi_population / 1e3).round(1)) + " K"
            )

        state_revenue = ubi_annual * state_ubi_population

        if state_revenue > 1e9:
            revenue_line = (
                "Funds for UBI ("
                + dropdown_state
                + "): $"
                + str((state_revenue / 1e9).round(1))
                + " B"
            )
        else:
            revenue_line = (
                "Funds for UBI ("
                + dropdown_state
                + "): $"
                + str((state_revenue / 1e6).round(1))
                + " M"
            )

    else:
        if ubi_population > 1e6:
            ubi_population_line = (
                "UBI Population: " + str((ubi_population / 1e6).round(1)) + " M"
            )
        else:
            ubi_population_line = (
                "UBI Population: " + str((ubi_population / 1e3).round(1)) + " K"
            )

    winners_line = "Percent better off: " + winners_string + "%"
    resources_line = "Average change in resources per person: $" + resources_string

    # ---------- populate economic breakdown bar chart ------------- #

    # Create x-axis labels for each chart
    econ_fig_x_lab = ["Poverty rate", "Poverty gap", "Gini index"]
    econ_fig_cols = [poverty_rate_change, poverty_gap_change, gini_change]
    econ_fig = go.Figure(
        [
            go.Bar(
                x=econ_fig_x_lab,
                y=econ_fig_cols,
                text=econ_fig_cols,
                hovertemplate=[
                    # poverty rates
                    "Original poverty rate: "
                    + original_poverty_rate_string
                    + "%<br><extra></extra>"
                    "New poverty rate: " + poverty_rate_string + "%",
                    # poverty gap
                    "Original poverty gap: $"
                    + original_poverty_gap_billions
                    + "B<br><extra></extra>"
                    "New poverty gap: $" + poverty_gap_billions + "B",
                    # gini
                    "Original Gini index: <extra></extra>"
                    + original_gini_string
                    + "<br>New Gini index: "
                    + gini_string,
                ],
                marker_color=BLUE,
            )
        ]
    )

    # Edit text and display the UBI amount and percent winners in title
    econ_fig.update_layout(
        uniformtext_minsize=10,
        uniformtext_mode="hide",
        plot_bgcolor="white",
        title_text="Economic overview",
        title_x=0.5,
        hoverlabel=dict(bgcolor="white", font_size=14, font_family="Roboto"),
        yaxis_tickformat="%",
    )
    econ_fig.update_traces(texttemplate="%{text:.1%f}", textposition="auto")

    econ_fig.update_xaxes(
        tickangle=0,
        title_text="",
        tickfont={"size": 14},
        title_standoff=25,
        title_font=dict(size=14, family="Roboto", color="black"),
    )

    econ_fig.update_yaxes(
        tickprefix="",
        tickfont={"size": 14},
        title_standoff=25,
        title_font=dict(size=14, family="Roboto", color="black"),
    )

    # ------------------ populate poverty breakdown charts ---------------- #

    breakdown_fig_x_lab = [
        "Child",
        "Adult",
        "People<br>with<br>disabilities",
        "White",
        "Black",
        "Hispanic",
    ]

    breakdown_fig_cols = [pov_breakdowns["changes"][demog] for demog in demogs]
    hovertemplate = [pov_breakdowns["strings"][demog] for demog in demogs]

    breakdown_fig = go.Figure(
        [
            go.Bar(
                x=breakdown_fig_x_lab,
                y=breakdown_fig_cols,
                text=breakdown_fig_cols,
                hovertemplate=hovertemplate,
                marker_color=BLUE,
            )
        ]
    )

    breakdown_fig.update_layout(
        uniformtext_minsize=10,
        uniformtext_mode="hide",
        plot_bgcolor="white",
        title_text="Poverty rate breakdown",
        title_x=0.5,
        hoverlabel=dict(bgcolor="white", font_size=14, font_family="Roboto"),
        yaxis_tickformat="%",
    )
    breakdown_fig.update_traces(texttemplate="%{text:.1%f}", textposition="auto")

    breakdown_fig.update_xaxes(
        tickangle=0,
        title_text="",
        tickfont={"size": 14},
        title_standoff=25,
        title_font=dict(size=14, family="Roboto", color="black"),
    )

    breakdown_fig.update_yaxes(
        tickprefix="",
        tickfont={"size": 14},
        title_standoff=25,
        title_font=dict(size=14, family="Roboto", color="black"),
    )

    return (
        ubi_line,
        revenue_line,
        ubi_population_line,
        winners_line,
        resources_line,
        econ_fig,
        breakdown_fig,
    )


@app.callback(
    Output("include-checklist", "options"),
    Input("include-checklist", "value"),
)
def update(checklist):
    """[summary]
    prevent users from excluding both adults and children
    Parameters
    ----------
    checklist : list
        takes the input "include-checklist" from the callback

    Returns
    -------
    "Include in UBI" checklist with correct options
    """
    if "adults" not in checklist:
        return [
            {"label": "Non-Citizens", "value": "non_citizens"},
            {"label": "Children", "value": "children", "disabled": True},
            {"label": "Adults", "value": "adults"},
        ]
    elif "children" not in checklist:
        return [
            {"label": "Non-Citizens", "value": "non_citizens"},
            {"label": "Children", "value": "children"},
            {"label": "Adults", "value": "adults", "disabled": True},
        ]
    else:
        return [
            {"label": "Non-Citizens", "value": "non_citizens"},
            {"label": "Children", "value": "children"},
            {"label": "Adults", "value": "adults"},
        ]


@app.callback(
    Output("benefits-checklist", "options"),
    Input("level", "value"),
)
def update(radio):

    if "state" in radio:
        return [
            {"label": "  Child Tax Credit", "value": "ctc", "disabled": True},
            {
                "label": "  Supplemental Security Income (SSI)",
                "value": "incssi",
                "disabled": True,
            },
            {
                "label": "  SNAP (food stamps)",
                "value": "spmsnap",
                "disabled": True,
            },
            {
                "label": "  Earned Income Tax Credit",
                "value": "eitcred",
                "disabled": True,
            },
            {
                "label": "  Unemployment benefits",
                "value": "incunemp",
                "disabled": True,
            },
            {
                "label": "  Energy subsidy (LIHEAP)",
                "value": "spmheat",
                "disabled": True,
            },
        ]
    else:
        return [
            {"label": "  Child Tax Credit", "value": "ctc"},
            {
                "label": "  Supplemental Security Income (SSI)",
                "value": "incssi",
            },
            {"label": "  SNAP (food stamps)", "value": "spmsnap"},
            {"label": "  Earned Income Tax Credit", "value": "eitcred"},
            {"label": "  Unemployment benefits", "value": "incunemp"},
            {"label": "  Energy subsidy (LIHEAP)", "value": "spmheat"},
        ]


@app.callback(
    Output("taxes-checklist", "options"),
    Input("level", "value"),
)
def update(radio):

    if "state" in radio:
        return [
            {"label": "Income taxes", "value": "fedtaxac"},
            {
                "label": "Employee side payroll",
                "value": "fica",
                "disabled": True,
            },
        ]
    else:
        return [
            {"label": "Income taxes", "value": "fedtaxac"},
            {"label": "Employee side payroll", "value": "fica"},
        ]


if __name__ == "__main__":
    app.run_server(debug=True, port=8000, host="127.0.0.1")
