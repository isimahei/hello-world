import json
import os
import boto3
from aws_gameday_quests.gdQuestsApi import GameDayQuestsApiClient
from check_team_account_lambda import evaluate_parameter_input, evaluate_role_input

# Standard AWS GameDay Quests Environment Variables
QUEST_ID = os.environ['QUEST_ID']
QUEST_API_BASE = os.environ['QUEST_API_BASE']
QUEST_API_TOKEN = os.environ['QUEST_API_TOKEN']
GAMEDAY_REGION = os.environ['GAMEDAY_REGION']

# Icebreaker Quest Environment Variables
QUEST_TEAM_STATUS_TABLE = os.environ['QUEST_TEAM_STATUS_TABLE']

dynamodb = boto3.resource('dynamodb')


# Expected event parameters: {'team_id': team_id,'key': key, 'value': value}
def lambda_handler(event, context):
	print(f"update_lambda invocation, event:{json.dumps(event, default=str)}, context: {str(context)}")

	# Instantiate the Quest API Client.
	quests_api_client = GameDayQuestsApiClient(QUEST_API_BASE, QUEST_API_TOKEN)
	# Check if event is running
	event_status = quests_api_client.get_event_status()
	if event_status['status'] != 'IN_PROGRESS':
		print(f"Event Status: {event_status['status']}, aborting UPDATE_LAMBDA")
		return

	quest_status = quests_api_client.get_quest_for_team(team_id=event['team_id'], quest_id=QUEST_ID)
	if quest_status['quest-state'] != 'IN_PROGRESS':
		print(f"Quest Status: {quest_status['quest-state']}, aborting UPDATE_LAMBDA")

	icebreaker_status_table = dynamodb.Table(QUEST_TEAM_STATUS_TABLE)
	dynamodb_response = icebreaker_status_table.get_item(Key={'team-id': event['team_id']})
	print(f"Retrieved Icebreaker team state for team {event['team_id']}: {json.dumps(dynamodb_response, default=str)}")
	team_data = dynamodb_response['Item']

	# keys cannot have underscores

	if event['key'] == "roleName":
		team_data = evaluate_role_input(quests_api_client=quests_api_client, team_data=team_data)
	elif event['key'] == "parameterValue":
		team_data = evaluate_parameter_input(quests_api_client=quests_api_client, team_data=team_data)
	else:
		print(f"Unknown input key {event['key']} encountered, ignoring.")

	print(f"Storing team data back to DynamoDb: {json.dumps(team_data, default=str)}")
	dynamodb_response = icebreaker_status_table.put_item(Item=team_data)
	print(f"Result: {json.dumps(dynamodb_response, default=str)}")
