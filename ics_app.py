import streamlit as st
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz
import pandas as pd
import re
from pathlib import Path
import numpy as np
import urllib.parse

REPO_ROOT = Path(__file__).parent
DEFAULT_CSV = REPO_ROOT / "combined_schedules_25_26.csv"

def parse_local_dt(date_str, time_str, tz):
    d = str(date_str).strip()
    t = str(time_str).strip()

    # Convert "19:00:00" -> "19:00"
    if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", t):
        t = t[:5]

    # Allow "7:00" as well as "07:00"
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"):
        try:
            naive = datetime.strptime(f"{d} {t}", fmt)
            return tz.localize(naive)
        except ValueError:
            pass
    return None

# Set Streamlit page configuration
st.set_page_config(
    page_title="HK Squash League Calendar Generator",
    page_icon="📅"
)

# Load the data
@st.cache_data
def load_data(csv_path: Path):
    df = pd.read_csv(csv_path)
    return df

# File input
df = load_data(Path(DEFAULT_CSV))

# Define the timezone you want to use
timezone = pytz.timezone('Asia/Hong_Kong')

# Create the Streamlit Interface
# Division Selection

# Define the order of the divisions
custom_order = ['Premier Main', '2', '3', '4', '5', '6', '7', '8A', '8B', '9', '10', 
                '11', '12', '13A', '13B', '13C','14', '15A', '15B', 'Premier Masters', 'M2', 'M3', 
                'M4', 'Premier Ladies', 'L2', 'L3', 'L4']

# Extract unique division
division = df['Division'].unique()

# Convert divisions to a Pandas Categorical type with the custom order
division = pd.Categorical(division, categories=custom_order, ordered=True)

# Sort the divisions based on the custom order
division = division.sort_values()

# Convert the divisions back to a list
division = division.tolist()

# Create title with space below
st.title('HK Squash League 2025/26 Calendar Generator')

# Add a page break without a line
st.markdown("""<br>""", unsafe_allow_html=True)

# Write instructions
st.write("This app allows you to generate a calendar file for your team's fixtures that you can import into your calendar of choice.")

# ---------------------------
# Division + Team selection IN A FORM
# ---------------------------

def abbreviate_team_name(team_name: str) -> str:
    """Replace long club names with abbreviations."""
    team_name = str(team_name)
    abbreviations = {
        'Hong Kong Football Club': 'HKFC',
        'Hong Kong Cricket Club': 'HKCC',
        'Kowloon Cricket Club': 'KCC',
        'Ladies Recreation Club': 'LRC',
        'United Services Recreation Club': 'USRC',
    }
    for full, short in abbreviations.items():
        team_name = team_name.replace(full, short)
    return team_name


# Build the sorted division list (you already did this above)
divisions = division  # reuse your existing 'division' list from earlier steps

with st.form("generate_form"):
    # 1) Pick division
    selected_division = st.selectbox("Select Division", divisions, key="division")

    # 2) Build team list based on picked division
    df_division = df[df["Division"] == selected_division].copy()
    teams = pd.unique(pd.concat([df_division["Home Team"], df_division["Away Team"]]))
    teams = [t for t in teams if t != "[BYE]"]
    teams = sorted(teams)

    # 3) Pick team
    selected_team = st.selectbox("Select Team", teams, key="team")

    # 4) Submit to generate ICS
    submitted = st.form_submit_button("Generate calendar")

if submitted:
    # Filter schedule for the selected team
    team_schedule = df_division[
        (
            (df_division["Home Team"] == selected_team) |
            (df_division["Away Team"] == selected_team)
        ) &
        (df_division["Away Team"] != "[BYE]")
    ].copy()

    from ics import Calendar, Event
    cal = Calendar()

    # Build events
    for _, row in team_schedule.iterrows():
        event = Event()

        home_team = row["Home Team"]
        away_team = row["Away Team"]
        venue     = str(row["Venue"]).strip()
        date_str  = str(row["Date"]).strip()
        time_str  = str(row["Time"]).strip()
        division_name = row["Division"]

        # Abbreviate names
        home_abbrev = abbreviate_team_name(home_team)
        away_abbrev = abbreviate_team_name(away_team)
        me_abbrev   = abbreviate_team_name(selected_team)

        # Title: home vs away or away @ home
        if selected_team == home_team:
            opponent_abbrev = away_abbrev
            event.name = f"{me_abbrev} vs {opponent_abbrev}"
        else:
            opponent_abbrev = home_abbrev
            event.name = f"{me_abbrev} @ {opponent_abbrev}"

        # Parse date/time robustly (handles HH:MM and HH:MM:SS)
        # If you already added a helper, call it here instead.
        try:
            try:
                naive_dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
            except ValueError:
                naive_dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
            start = timezone.localize(naive_dt)
        except ValueError:
            st.error(f"Error parsing date/time: {home_abbrev} vs {away_abbrev} on {date_str} {time_str}")
            continue

        event.begin = start
        event.end   = start + timedelta(hours=2.5)
        event.location    = venue
        event.description = f"Division: {division_name}"
        # Optional: add a stable UID to avoid duplicates on import
        event.uid = f"hk-squash-{me_abbrev}-{opponent_abbrev}-{start:%Y%m%dT%H%M%z}"

        cal.events.add(event)

    if len(cal.events) == 0:
        st.error("None of this team's fixtures had a valid date/time, so the calendar is empty.")
    else:
        # --- iPhone-friendly: store BYTES in session_state and render button immediately ---
        ics_bytes = cal.serialize().encode("utf-8")
        st.session_state["ics_bytes"] = ics_bytes
        st.session_state["ics_filename"] = f'{selected_team}_fixtures.ics'.replace(' ', '_').lower()

# ---------------------------
# Download area (outside the form)
# ---------------------------
if "ics_bytes" in st.session_state:
    st.download_button(
        label="**Download Schedule**",
        data=st.session_state["ics_bytes"],   # BYTES, not str
        file_name=st.session_state["ics_filename"],
        mime="text/calendar",
        key="dl_ics"  # stable key prevents stale ephemeral URL on iOS
    )

    # Optional iPhone fallback (data: URI)
    ics_text = st.session_state["ics_bytes"].decode("utf-8")
    data_uri = "data:text/calendar;charset=utf-8," + urllib.parse.quote(ics_text)
    st.markdown(f"[Open in Calendar (fallback)]({data_uri})", unsafe_allow_html=True)

# ---------------------------
# (Optional) Fixture list display below — this doesn’t create widgets, so won’t re-run
# ---------------------------
if submitted and len(cal.events) > 0:
    # Build a lightweight display frame without mutating team_schedule
    opponent = np.where(
        team_schedule["Home Team"].eq(selected_team),
        team_schedule["Away Team"],
        team_schedule["Home Team"]
    )
    schedule_to_display = pd.DataFrame({
        "Date": team_schedule["Date"].values,
        "Opponent": pd.Series(opponent).map(abbreviate_team_name),
        "Venue": team_schedule["Venue"].values,
    }).reset_index(drop=True)

    st.markdown(f"### Fixture List for {selected_team}")
    st.dataframe(schedule_to_display, use_container_width=True)


# Add instructions to import the ICS file in different calendars
st.markdown("""
### How to Import Your ICS File
Follow the steps below to import the ICS file into your preferred calendar:

#### **Google Calendar**
1. Open **Google Calendar** on your computer (use the web version).
2. On the left-hand side, click the **+** next to "Other calendars."
3. Select **Import**.
4. Click **Select file from your computer** and upload the downloaded `.ics` file.
5. Choose the calendar you want to import the events to.
6. Click **Import**.

#### **Outlook Calendar**
1. Open **Outlook** and go to your calendar.
2. Click **File** in the top menu.
3. Select **Open & Export**, then choose **Import/Export**.
4. Choose **Import an iCalendar (.ics) or vCalendar file** and click **Next**.
5. Find and select the downloaded `.ics` file, then choose **Import**.

#### **Apple Calendar (iCal)**
1. Open the **Calendar** app on your Mac.
2. In the menu bar, go to **File** and select **Import**.
3. Locate and select the downloaded `.ics` file, then click **Import**.
4. Choose the calendar you want to add the events to, and click **OK**.
""")
