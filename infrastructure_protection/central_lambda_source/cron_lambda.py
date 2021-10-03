import os
import boto3
import json
from aws_gameday_quests.gdQuestsApi import GameDayQuestsApiClient

# Standard AWS GameDay Quests Environment Variables
QUEST_ID = os.environ['QUEST_ID']
QUEST_API_BASE = os.environ['QUEST_API_BASE']
QUEST_API_TOKEN = os.environ['QUEST_API_TOKEN']
GAMEDAY_REGION = os.environ['GAMEDAY_REGION']

# Icebreaker Quest Environment Variables
CHECK_TEAM_ACCOUNT_LAMBDA = os.environ['CHECK_TEAM_ACCOUNT_LAMBDA']
QUEST_TEAM_STATUS_TABLE = os.environ['QUEST_TEAM_STATUS_TABLE']

# Lambda Client Setup
lambda_client = boto3.client('lambda')


def lambda_handler(event, context):
    print(f"cron_lambda invocation, event:{json.dumps(event, default=str)}, context: {str(context)}")

    # Instantiate the Quest API Client.
    quests_api_client = GameDayQuestsApiClient(QUEST_API_BASE, QUEST_API_TOKEN)
    # Check if event is running
    event_status = quests_api_client.get_event_status()
    if event_status['status'] != 'IN_PROGRESS':
        print(f"Event Status: {event_status}, aborting CRON_LAMBDA")
        return

    # Get all teams that are in any way engaging with this Quest
    active_teams = quests_api_client.get_teams_for_quest(QUEST_ID)
    print(f"Active teams to fan out checks: {active_teams}")

    # Find IN_PROGRESS teams and evaluate them
    for team in active_teams:
        if team['quest-state'] == "IN_PROGRESS":
            lambda_response = lambda_client.invoke(
                FunctionName=CHECK_TEAM_ACCOUNT_LAMBDA,
                InvocationType='Event',
                Payload=json.dumps(team, default=str))
            print(f"Fanned out check for team {team['team-id']}, " +
                  f"async Lambda invocation response: {json.dumps(lambda_response, default=str)}")
        else:
            print(f"Skipping team {team['team-id']} with Quest status: {team['quest-state']}")
