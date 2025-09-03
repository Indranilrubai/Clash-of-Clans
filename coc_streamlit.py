import streamlit as st
import pandas as pd
from requests import Session
from urllib.parse import quote
from collections import defaultdict
import time

# --- CONFIG ---
CLAN_TAG = "#P2Y8RL9C"
API_KEY = st.secrets["API_KEY"]
CLAN_TAG = st.secrets["CLAN_TAG"]
BASE_URL = "https://api.clashofclans.com/v1/"
# -------------

def calculate_score(stars, destruction):
    if stars == 3:
        return 5
    elif stars == 2:
        return 4 if destruction >= 90 else 3
    elif stars == 1:
        return 1
    else:
        return 0

def retrieve_war_tags(session):
    url = f"{BASE_URL}clans/{quote(CLAN_TAG)}/currentwar/leaguegroup"
    response = session.get(url)
    response.raise_for_status()
    data = response.json()
    war_tags = [war['warTags'] for war in data.get('rounds', [])]
    war_tags = [item for sublist in war_tags for item in sublist if item != '#0']
    return war_tags

def retrieve_and_score_war_data(session, war_tags):
    all_players_scores = defaultdict(lambda: defaultdict(lambda: {'score': 0, 'in_war': False, 'attacks_count': 0}))
    clan_war_no = 0

    for i, war_tag in enumerate(war_tags):
        url = f"{BASE_URL}clanwarleagues/wars/{quote(war_tag)}"
        response = session.get(url)
        response.raise_for_status()
        war_data = response.json()

        if war_data.get('state', "preparation") == "preparation":
            continue

        our_clan = None
        if war_data.get('clan', {}).get('tag') == CLAN_TAG:
            our_clan = war_data['clan']
        elif war_data.get('opponent', {}).get('tag') == CLAN_TAG:
            our_clan = war_data['opponent']

        if not our_clan:
            continue

        clan_war_no += 1
        for member in our_clan.get('members', []):
            player_tag = member.get('tag')
            player_name = member.get('name', 'N/A')

            player_stats = all_players_scores[player_tag]
            player_stats['name'] = player_name
            player_stats[f'War {clan_war_no}']['in_war'] = True

            attacks = member.get('attacks', [])
            if attacks:
                player_stats[f'War {clan_war_no}']['attacks_count'] = len(attacks)
                for attack in attacks:
                    score = calculate_score(attack.get('stars', 0), attack.get('destructionPercentage', 0))
                    player_stats[f'War {clan_war_no}']['score'] += score

        time.sleep(1)  # Respect API rate limits

    return all_players_scores, clan_war_no

# --- Streamlit App ---
st.title("🏆 Clash of Clans CWL Performance Tracker")

if st.button("Fetch CWL Data"):
    with Session() as session:
        session.headers.update({
            "Accept": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        })

        st.write("Fetching CWL war tags...")
        try:
            war_tags = retrieve_war_tags(session)
            if not war_tags:
                st.error("No CWL war tags found.")
            else:
                players_scores, total_wars = retrieve_and_score_war_data(session, war_tags)

                # Convert results to DataFrame
                rows = []
                for tag, stats in players_scores.items():
                    row = {"Tag": tag, "Name": stats["name"]}
                    total_score = 0
                    for i in range(1, total_wars + 1):
                        war_data = stats.get(f'War {i}')
                        score = 0
                        if not war_data['in_war']:
                            score = 2
                        elif war_data['attacks_count'] == 0:
                            score = -3
                        else:
                            score = war_data['score']
                        row[f"War {i} Score"] = score
                        total_score += score
                    row["Total CWL Score"] = total_score
                    rows.append(row)

                df = pd.DataFrame(rows)
                st.success("✅ Data fetched successfully!")
                st.dataframe(df)

        except Exception as e:
            st.error(f"Error fetching data: {e}")


