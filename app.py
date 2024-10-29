from espn_api.football import League
import openai
import streamlit as st

# Initialize OpenAI API client with st.secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Streamlit UI for user input
st.title("🏈 Fantasy Football Weekly Recap Bot")
st.write("Enter your league details to generate a humorous, detailed weekly recap for your league.")
st.write("For SW2 and ESPN_S2: https://www.gamedaybot.com/help/espn_s2-and-swid/")
st.write("For League ID: Go to your league's homepage on ESPN and copy the number at the end of the URL.")

# User Inputs
league_id = st.text_input("League ID", help="Your ESPN Fantasy Football league ID.")
year = st.number_input("Year", min_value=2000, max_value=2024, value=2024, help="Fantasy season year.")
swid = st.text_input("SWID", help="Your ESPN SWID cookie value.")
espn_s2 = st.text_input("ESPN_S2", help="Your ESPN_S2 cookie value.")

if st.button("Generate Weekly Recap"):
    if not league_id or not swid or not espn_s2:
        st.error("Please enter all required information.")
    else:
        # Initialize the league connection with user-provided data
        league = League(league_id=int(league_id), year=year, espn_s2=espn_s2, swid=swid)

        # Function to collect league summary
        def get_comprehensive_league_summary():
            summary = "Fantasy Football Weekly Recap:\n\n"

            # Standings and Records
            summary += "League Standings and Records:\n"
            standings = sorted(league.teams, key=lambda x: x.points_for, reverse=True)
            for team in standings:
                # Formatting playoff percentages correctly
                playoff_chance = f"{team.playoff_pct / 100:.2%}" if hasattr(team, 'playoff_pct') else "N/A"
                summary += f"{team.team_name}: {team.wins}-{team.losses} (PF: {team.points_for}, PA: {team.points_against}) - Playoff Chance: {playoff_chance}\n"

            # Top Performers Across Teams (Based on recent weekly performance)
            summary += "\nTop Performers by Team:\n"
            for team in league.teams:
                try:
                    top_player = max(team.roster, key=lambda x: x.total_points, default=None)
                    if top_player:
                        summary += f"{team.team_name} - Best Player: {top_player.name} ({top_player.position}) with {top_player.total_points} points\n"
                except AttributeError:
                    summary += f"{team.team_name} - Best Player: Data not available for individual player points\n"

            # Matchups and Highest Scoring Team for Last Week
            current_week = league.current_week
            last_week = current_week - 1
            summary += f"\nMatchups - Week {last_week}:\n"
            matchups = league.scoreboard(week=last_week)
            highest_score = 0
            highest_scoring_team = None

            for match in matchups:
                summary += (f"{match.home_team.team_name} ({match.home_score} points) vs "
                            f"{match.away_team.team_name} ({match.away_score} points)\n")

                # Check for highest scorer of the week
                if match.home_score > highest_score:
                    highest_score = match.home_score
                    highest_scoring_team = match.home_team.team_name
                if match.away_score > highest_score:
                    highest_score = match.away_score
                    highest_scoring_team = match.away_team.team_name

            # Highlight Big Matchup for This Week
            summary += f"\nBig Matchup - Week {current_week}:\n"
            upcoming_matchups = league.scoreboard(week=current_week)
            big_matchup = sorted(upcoming_matchups, key=lambda x: (x.home_team.wins + x.away_team.wins), reverse=True)[0]
            summary += (
                f"{big_matchup.home_team.team_name} (Record: {big_matchup.home_team.wins}-{big_matchup.home_team.losses}) vs "
                f"{big_matchup.away_team.team_name} (Record: {big_matchup.away_team.wins}-{big_matchup.away_team.losses})\n")

            # Weekly Highlights
            summary += "\nWeekly Highlights:\n"
            summary += f"Highest Scoring Team Last Week: {highest_scoring_team} with {highest_score} points\n"
            closest_game = min(matchups, key=lambda x: abs(x.home_score - x.away_score))
            summary += (f"Closest Game: {closest_game.home_team.team_name} vs {closest_game.away_team.team_name} "
                        f"with a score difference of {abs(closest_game.home_score - closest_game.away_score)}\n")

            return summary

        # Generate a humorous recap using OpenAI
        def generate_funny_recap(summary):
            prompt = f"Create a funny, sarcastic weekly recap based on this fantasy football data:\n\n{summary}"
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system",
                     "content": "You are a very raunchy, explicit and sarcastic commentator providing a humorous recap of a "
                                "fantasy football league’s weekly results. Be extremely explicit and make fun of the bad "
                                "teams in detail including their name. Make sure to create different sections with bold headings "
                                "for each part of the recap. Player scores and Team Scores are total for the season. Do not "
                                "include yourself in the recap. Cover these as sections. Best teams, Most Ass teams, last week's"
                                "matchups and big matchup of the week. Make sure every team is mentioned at some point"},
                    {"role": "user",
                     "content": prompt}
                ],
                max_tokens=1300,
                temperature=0.7
            )

            recap_text = response.choices[0].message.content
            return recap_text.strip()

        try:
            # Collect data and generate recap
            summary = get_comprehensive_league_summary()
            st.write("**League Data Summary:**")
            st.text(summary)

            recap = generate_funny_recap(summary)
            st.write("**Funny Weekly Recap:**")
            st.write(recap)
            st.write(\n"**Based on app built from Jeisey**")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
