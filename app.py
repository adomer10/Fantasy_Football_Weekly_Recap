from espn_api.football import League
import openai
import streamlit as st
import pandas as pd

# App title and option selection
st.title("🏈 Fantasy Football Team Analysis and Trade Suggestions")

# User selects between Weekly Recap and Detailed Team Analysis
option = st.radio("Select an Option", ["Weekly Recap", "Detailed Team Analysis"])

# Load player data
player_data = pd.read_csv('FantasyPros_2024_Ros_ALL_Rankings.csv')

# Initialize OpenAI API client with st.secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Sidebar for entering league details
with st.sidebar:
    st.header("Enter League Details")
    st.write("For SWID and ESPN_S2: [Help Guide](https://www.gamedaybot.com/help/espn_s2-and-swid/)")
    st.write("For League ID: Go to your league's homepage on ESPN and copy the number at the end of the URL.")

    # User Inputs in the Sidebar
    league_id = st.text_input("League ID", help="Your ESPN Fantasy Football league ID.")
    year = st.number_input("Year", min_value=2000, max_value=2024, value=2024, help="Fantasy season year.")
    swid = st.text_input("SWID", help="Your ESPN SWID cookie value.")
    espn_s2 = st.text_input("ESPN_S2", help="Your ESPN_S2 cookie value.")

# Initialize the league connection
league = None
if league_id and swid and espn_s2:
    try:
        league = League(league_id=int(league_id), year=year, espn_s2=espn_s2, swid=swid)
    except Exception as e:
        st.error(f"Failed to initialize league: {e}")


# Function to collect league summary
def get_comprehensive_league_summary():
    try:
        summary = "Fantasy Football Weekly Recap:\n\n"
        standings = sorted(league.teams, key=lambda x: x.points_for, reverse=True)

        summary += "League Standings and Records:\n"
        for team in standings:
            playoff_chance = f"{team.playoff_pct / 100:.2%}" if hasattr(team, 'playoff_pct') else "N/A"
            summary += f"{team.team_name}: {team.wins}-{team.losses} (PF: {team.points_for}, PA: {team.points_against}) - Playoff Chance: {playoff_chance}\n"

        summary += "\nTop Performers by Team:\n"
        for team in league.teams:
            top_player = max(team.roster, key=lambda x: x.total_points, default=None)
            if top_player:
                summary += f"{team.team_name} - Best Player: {top_player.name} ({top_player.position}) with {top_player.total_points} points\n"

        current_week = league.current_week
        last_week = current_week - 1
        matchups = league.scoreboard(week=last_week)
        highest_score, highest_scoring_team = 0, None
        summary += f"\nMatchups - Week {last_week}:\n"
        for match in matchups:
            summary += f"{match.home_team.team_name} ({match.home_score} points) vs {match.away_team.team_name} ({match.away_score} points)\n"
            if match.home_score > highest_score:
                highest_score, highest_scoring_team = match.home_score, match.home_team.team_name
            if match.away_score > highest_score:
                highest_score, highest_scoring_team = match.away_score, match.away_team.team_name

        summary += f"\nWeekly Highlights:\nHighest Scoring Team Last Week: {highest_scoring_team} with {highest_score} points\n"
        closest_game = min(matchups, key=lambda x: abs(x.home_score - x.away_score))
        summary += f"Closest Game: {closest_game.home_team.team_name} vs {closest_game.away_team.team_name} with a score difference of {abs(closest_game.home_score - closest_game.away_score)}\n"

        return summary
    except Exception as e:
        st.error(f"Failed to generate league summary: {e}")
        return ""


# Generate a humorous recap using OpenAI
def generate_funny_recap(summary):
    try:
        prompt = f"Create a funny, sarcastic weekly recap based on this fantasy football data:\n\n{summary}"
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "You are providing a very raunchy, explicit and sarcastichumorous recap of a "
                            "fantasy football league’s weekly results. Be extremely explicit and make fun of the bad "
                            "teams in detail including their name. Make sure to create different sections with bold headings "
                            "for each part of the recap. Individual player scores are total for season, so don't include when talking about previous week. Do not "
                            "include yourself in the recap. Cover these as sections: Best teams, Most Ass teams, last week's"
                            "matchups and Fraud Alert. Make sure every team is mentioned at some point. Profanity and Vulgarness is encouraged."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1300,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Failed to generate recap: {e}")
        return ""

def analyze_team_and_suggest_trades(team_name, player_data, league):
    # Locate the user's team in the league
    user_team = next((team for team in league.teams if team.team_name == team_name), None)
    if not user_team:
        return f"No team found with the name {team_name}."

    # Initial team analysis for strengths, weaknesses, and standings
    analysis = f"Team Analysis for {team_name}:\n\n"
    analysis += "### Positional Overview:\n"

    # Collect roster composition, projected points, and identify weak spots
    roster_info = ""
    weak_spots = []
    for player in user_team.roster:
        # Find the player in the CSV data
        player_row = player_data[player_data['PLAYER NAME'] == player.name]

        if not player_row.empty:
            # Extract the player's rank and projected points
            rank = player_row.iloc[0]['RK']
            projected_points = player_row.iloc[0].get('PROJECTED POINTS', 0)  # Assuming a 'PROJECTED POINTS' column
            roster_info += f"- {player.name} ({player.position}), Rank: {rank}, Projected Points: {projected_points}\n"

            # Identify weak spots based on rank and projected points
            if rank > 60:  # Adjust threshold as needed
                weak_spots.append({
                    "player_name": player.name,
                    "position": player.position,
                    "rank": rank,
                    "projected_points": projected_points
                })

    # Include roster information in the analysis
    analysis += f"Current Roster:\n{roster_info}\n\n"

    # Add team standings and playoff chances for context
    playoff_chance = f"{user_team.playoff_pct / 100:.2%}" if hasattr(user_team, 'playoff_pct') else "N/A"
    analysis += f"### Current Standings:\n"
    analysis += f"- Record: {user_team.wins}-{user_team.losses}\n"
    analysis += f"- Points For: {user_team.points_for}\n"
    analysis += f"- Points Against: {user_team.points_against}\n"
    analysis += f"- Playoff Chance: {playoff_chance}\n\n"

    # Compile league-wide data: team names, records, and rosters
    league_data = "### League Teams and Rosters:\n"
    all_rostered_players = set(player.name for team in league.teams for player in team.roster)

    for team in league.teams:
        team_roster = [f"{player.name} ({player.position})" for player in team.roster]
        league_data += (f"- Team: {team.team_name}\n"
                        f"  - Record: {team.wins}-{team.losses}\n"
                        f"  - Playoff Chance: {team.playoff_pct if hasattr(team, 'playoff_pct') else 'N/A'}%\n"
                        f"  - Roster: {', '.join(team_roster)}\n\n")

    # Filter player_data to find only waiver wire players (those not in any team's roster)
    waiver_info = "### Waiver Wire Players:\n"
    waiver_players = player_data[~player_data['PLAYER NAME'].isin(all_rostered_players)]
    for _, row in waiver_players.iterrows():
        waiver_info += f"- {row['PLAYER NAME']} ({row['POS']}), Rank: {row['RK']}, Projected Points: {row.get('PROJECTED POINTS', 0)}\n"

    # Construct the full prompt for GPT-4
    prompt = (f"Here’s a detailed analysis of the fantasy football team '{team_name}', including strengths, "
              f"weaknesses, standings, and trade recommendations.\n\n{analysis}\n\n{league_data}\n\n{waiver_info}\n\n"
              f"Based on this information, suggest reasonable trade packages that would address the team’s weak "
              f"spots.")
    # GPT-4 final analysis and trade recommendations
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system",
             "content": "You are a fantasy football analyst providing insights and trade recommendations. Using the "
                        "provide rankings create mock trades with other teams and confidently suggest trades. "
                        "Also make sure to provide a detailed analysis of the team's strengths and weaknesses."
                        "Include the team's current standings and playoff chances as part of the analysis "
                        "and reasoning to possibly be more aggressive or vice versa. Make specific trade suggestions "
                        "listing the other team and what the entire package could look like. Also include waiver "
                        "pickups, only using players that are not rostered in the league."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1300,
        temperature=0.5
    )

    return response.choices[0].message.content.strip()

# Display content based on the selected option
if option == "Weekly Recap" and league:
    if st.button("Generate Weekly Recap"):
        with st.spinner("Generating weekly recap..."):
            summary = get_comprehensive_league_summary()
            if summary:
                recap = generate_funny_recap(summary)
                st.write(recap)
                st.write('\n\nBased on app built from Jeisey on github')

elif option == "Detailed Team Analysis" and league:
    st.subheader("Select Your Team for Analysis")
    team_names = [team.team_name for team in league.teams]
    team_name = st.selectbox("Choose your team:", team_names)

    if st.button("Get Team Analysis and Trade Suggestions") and team_name:
        with st.spinner("Analyzing team and generating trade suggestions..."):
            team_analysis = analyze_team_and_suggest_trades(team_name, player_data, league)
            st.write("**Detailed Team Analysis and Trade Suggestions:**")
            st.write(team_analysis)
            st.write('\n\nBased on app built from Jeisey')
            st.write('\nData Source: [FantasyPros](https://www.fantasypros.com/)')')
