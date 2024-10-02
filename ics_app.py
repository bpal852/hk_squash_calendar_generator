import streamlit as st
from ics import Calendar, Event
from datetime import datetime, timedelta
import pytz
import pandas as pd

# Set Streamlit page configuration
st.set_page_config(
    page_title="HK Squash League Calendar Generator",
    page_icon="📅"
)


# Load the data
@st.cache_data
def load_data():
    df = pd.read_csv('schedules_24_25.csv')
    return df


df = load_data()

# Define the timezone you want to use
timezone = pytz.timezone('Asia/Hong_Kong')

# Create the Streamlit Interface
# Division Selection

# Define the order of the divisions
custom_order = ['Premier Main', '2', '3', '4', '5', '6', '7A', '7B', '8A', '8B', '9', '10', 
                '11', '12', '13A', '13B', '14', '15A', '15B', 'Premier Masters', 'M2', 'M3', 
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
st.title('HK Squash League 2024/25 Calendar Generator')

# Add a page break without a line
st.markdown("""<br>""", unsafe_allow_html=True)

# Write instructions
st.write("This app allows you to generate a calendar file for your team's fixtures that you can import into your calendar of choice.")

# Select division
selected_division = st.selectbox('Select Division', division)

# Team Selection
# Filter dataframe to the selected division
df_division = df[df['Division'] == selected_division]

# Get unique teams from 'Home Team' and 'Away Team'
teams = pd.unique(pd.concat([df_division['Home Team'], df_division['Away Team']]))

# Discard 'Bye' from the list of teams
teams = [team for team in teams if team != '[BYE]']
teams = sorted(teams)

# Team selection
selected_team = st.selectbox('Select Team', teams)
# Filter schedule for the selected team
team_schedule = df_division[
    (
        (df_division['Home Team'] == selected_team) |
        (df_division['Away Team'] == selected_team)
    ) &
    (df_division['Away Team'] != '[BYE]')
]

# Define abbreviation function
def abbreviate_team_name(team_name):
    abbreviations = {
        'Hong Kong Football Club': 'HKFC',
        'Hong Kong Cricket Club': 'HKCC',
        'Kowloon Cricket Club': 'KCC',
        'Ladies Recreation Club': 'LRC',
        'United Services Recreation Club': 'USRC',
    }
    for full_name, abbreviation in abbreviations.items():
        team_name = team_name.replace(full_name, abbreviation)
    return team_name

# Generate the ICS file
if team_schedule.empty:
    st.warning("No schedule found for the selected team.")
    st.stop()
else:
    cal = Calendar()
    for _, row in team_schedule.iterrows():
        event = Event()

        home_team = row['Home Team']
        away_team = row['Away Team']
        venue = row['Venue']
        date_str = row['Date']
        time_str = row['Time']
        division = row['Division']

        # Abbreviate the team names
        home_team_abbrev = abbreviate_team_name(home_team)
        away_team_abbrev = abbreviate_team_name(away_team)
        selected_team_abbrev = abbreviate_team_name(selected_team)

        # Determine if the selected team is the home team or away team
        if selected_team == home_team:
            opponent = away_team
            opponent_abbrev = away_team_abbrev
            event.name = f'{selected_team_abbrev} vs {opponent_abbrev}'
        else:
            opponent = home_team
            opponent_abbrev = home_team_abbrev
            event.name = f'{selected_team_abbrev} @ {opponent_abbrev}'

        # Parse the date and time, and localize it to the specified timezone
        try:
            naive_datetime = datetime.strptime(f'{date_str} {time_str}', "%d/%m/%Y %H:%M")
            localized_datetime = timezone.localize(naive_datetime)
        except ValueError:
            st.error(f"Error parsing date or time for match: {home_team_abbrev} vs {away_team_abbrev} on {date_str} {time_str}")
            continue

        # Set beginning and end of the event
        event.begin = localized_datetime
        event.end = localized_datetime + timedelta(hours=2.5)

        # Set the location and description of the event
        event.location = venue
        event.description = f'Division: {division}'

        # Add the event to the calendar
        cal.events.add(event)

        # Convert the calendar to a string
        ics_content = cal.serialize()

# Add a page break without a line
st.markdown("""<br>""", unsafe_allow_html=True)

# Provide download option
st.download_button(
    label='**Download Schedule**',
    data=ics_content,
    file_name=f'{selected_team}_fixtures.ics'.replace(' ', '_').lower(),
    mime='text/calendar'
)

# Add a page break without a line
st.markdown("""<br>""", unsafe_allow_html=True)

# Create an opponent column based on home/away team
team_schedule['Opponent'] = team_schedule.apply(
    lambda row: row['Away Team'] if row['Home Team'] == selected_team else row['Home Team'], axis=1
)

# Abbreviate team names in the 'Opponent' column
team_schedule['Opponent'] = team_schedule['Opponent'].apply(abbreviate_team_name)

# Select only the relevant columns (Date, Opponent, Venue)
schedule_to_display = team_schedule[['Date', 'Opponent', 'Venue']]

# Reset index and drop the original index
schedule_to_display = schedule_to_display.reset_index(drop=True)

# Use the to_html method to render the table without the index
schedule_html = schedule_to_display.to_html(index=False)

# Add custom CSS for left-aligning the headers
schedule_html = schedule_html.replace('<th>', '<th style="text-align: left;">')

if not team_schedule.empty:
    st.markdown(f"### Fixture List for {selected_team}")
    st.markdown(schedule_html, unsafe_allow_html=True)

# Add a page break without a line
st.markdown("""<br>""", unsafe_allow_html=True)

# Add a page break without a line
st.markdown("""<br>""", unsafe_allow_html=True)

# Add a page break
st.markdown("""---""")

# Add a page break without a line
st.markdown("""<br>""", unsafe_allow_html=True)

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
